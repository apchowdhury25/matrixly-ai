"""
Calendar backends: local (default), Google Calendar stub, Calendly-style API.

Local backend is production-ready for SMBs without OAuth setup.
Google/Calendly activate when credentials are present.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from ..models import Booking, SlotProposal, utc_now
from ..services.bookings import BookingStore


def _tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def parse_hhmm(s: str) -> tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)


class CalendarService:
    def __init__(self, cfg: dict, bookings: BookingStore) -> None:
        self.cfg = cfg
        self.bookings = bookings
        data = Path(cfg["paths"]["data"])
        self.local_busy_path = data / "calendar" / "busy.json"
        self.local_busy_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.local_busy_path.exists():
            self.local_busy_path.write_text("[]", encoding="utf-8")

    @property
    def backend(self) -> str:
        return ((self.cfg.get("calendar") or {}).get("backend") or "local").lower()

    def business_tz(self) -> str:
        return (self.cfg.get("business") or {}).get("timezone") or "America/Chicago"

    def service_meta(self, service_id: str) -> dict[str, Any]:
        services = self.cfg.get("services") or []
        for s in services:
            if s.get("id") == service_id:
                return s
        book = self.cfg.get("booking") or {}
        return {
            "id": service_id,
            "name": service_id.title(),
            "duration_minutes": int(book.get("default_duration_minutes") or 30),
        }

    def list_busy(self) -> list[tuple[datetime, datetime]]:
        intervals = list(self.bookings.busy_intervals())
        # Local extra busy blocks
        try:
            raw = json.loads(self.local_busy_path.read_text(encoding="utf-8"))
            for row in raw:
                s = datetime.fromisoformat(row["start"].replace("Z", "+00:00"))
                e = datetime.fromisoformat(row["end"].replace("Z", "+00:00"))
                if s.tzinfo is None:
                    s = s.replace(tzinfo=timezone.utc)
                if e.tzinfo is None:
                    e = e.replace(tzinfo=timezone.utc)
                intervals.append((s, e))
        except Exception:
            pass
        if self.backend == "google":
            intervals.extend(self._google_busy())
        return intervals

    def _overlaps(
        self,
        start: datetime,
        end: datetime,
        busy: list[tuple[datetime, datetime]],
        buf_before: timedelta,
        buf_after: timedelta,
    ) -> bool:
        a = start - buf_before
        b = end + buf_after
        for s, e in busy:
            if a < e and b > s:
                return True
        return False

    def propose_slots(
        self,
        service_id: str = "consult",
        preferred_date: str | None = None,
        preferred_time: str | None = None,
        max_proposals: int | None = None,
    ) -> list[SlotProposal]:
        book = self.cfg.get("booking") or {}
        hours_cfg = self.cfg.get("business_hours") or {}
        tz_name = self.business_tz()
        tz = _tz(tz_name)
        duration = int(
            self.service_meta(service_id).get("duration_minutes")
            or book.get("default_duration_minutes")
            or 30
        )
        step = int(book.get("slot_step_minutes") or 30)
        buf_b = timedelta(minutes=int(book.get("buffer_before_minutes") or 10))
        buf_a = timedelta(minutes=int(book.get("buffer_after_minutes") or 10))
        max_days = int(book.get("max_days_ahead") or 14)
        min_notice = timedelta(hours=float(book.get("min_notice_hours") or 2))
        limit = max_proposals or int(book.get("max_proposals") or 5)

        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(tz)
        busy = self.list_busy()

        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]

        proposals: list[SlotProposal] = []
        # Prefer starting day if preferred_date provided
        start_offset = 0
        if preferred_date:
            try:
                pref = datetime.strptime(preferred_date, "%Y-%m-%d").date()
                delta = (pref - now_local.date()).days
                if 0 <= delta <= max_days:
                    start_offset = delta
            except ValueError:
                pass

        for day_i in range(start_offset, max_days + 1):
            day = (now_local + timedelta(days=day_i)).date()
            weekday = day_names[day.weekday()]
            window = hours_cfg.get(weekday)
            if not window:
                continue
            sh, sm = parse_hhmm(window["start"])
            eh, em = parse_hhmm(window["end"])
            cursor = datetime(day.year, day.month, day.day, sh, sm, tzinfo=tz)
            end_day = datetime(day.year, day.month, day.day, eh, em, tzinfo=tz)

            while cursor + timedelta(minutes=duration) <= end_day:
                slot_end = cursor + timedelta(minutes=duration)
                start_utc = cursor.astimezone(timezone.utc)
                end_utc = slot_end.astimezone(timezone.utc)

                if start_utc < now_utc + min_notice:
                    cursor += timedelta(minutes=step)
                    continue

                if preferred_time:
                    pt = preferred_time.lower()
                    if pt in {"morning", "afternoon"}:
                        if pt == "morning" and cursor.hour >= 12:
                            cursor += timedelta(minutes=step)
                            continue
                        if pt == "afternoon" and cursor.hour < 12:
                            cursor += timedelta(minutes=step)
                            continue
                    elif ":" in pt:
                        try:
                            ph, pm = parse_hhmm(pt[:5])
                            if cursor.hour != ph or cursor.minute != pm:
                                # allow nearby slots within 60m
                                if abs((cursor.hour * 60 + cursor.minute) - (ph * 60 + pm)) > 60:
                                    cursor += timedelta(minutes=step)
                                    continue
                        except Exception:
                            pass

                if not self._overlaps(start_utc, end_utc, busy, buf_b, buf_a):
                    label = cursor.strftime("%a %b %d · %I:%M %p %Z")
                    score = 1.0
                    if preferred_date and day.isoformat() == preferred_date:
                        score += 0.3
                    if preferred_time and preferred_time.lower() not in {"morning", "afternoon"}:
                        score += 0.2
                    proposals.append(
                        SlotProposal(
                            start_iso=start_utc.isoformat(),
                            end_iso=end_utc.isoformat(),
                            label=label,
                            service_id=service_id,
                            score=score,
                        )
                    )
                    if len(proposals) >= limit:
                        proposals.sort(key=lambda p: (-p.score, p.start_iso))
                        return proposals[:limit]

                cursor += timedelta(minutes=step)

            # If preferred day had no slots, continue to next days
            if preferred_date and day_i == start_offset and not proposals:
                continue

        proposals.sort(key=lambda p: (-p.score, p.start_iso))
        return proposals[:limit]

    def create_event(self, booking: Booking) -> str | None:
        """Create calendar event; returns external event id if any."""
        if self.backend == "google":
            eid = self._google_create(booking)
            if eid:
                return eid
        if self.backend == "calendly":
            # Calendly typically books via invitee API; log intent
            return f"calendly-local-{booking.id}"
        # Local mirror
        busy = []
        try:
            busy = json.loads(self.local_busy_path.read_text(encoding="utf-8"))
        except Exception:
            busy = []
        busy.append(
            {
                "start": booking.start_iso,
                "end": booking.end_iso,
                "booking_id": booking.id,
                "title": f"{booking.service_name} — {booking.customer.name or booking.customer.email}",
                "created_at": utc_now(),
            }
        )
        self.local_busy_path.write_text(json.dumps(busy, indent=2), encoding="utf-8")
        return f"local-{booking.id}"

    def delete_event(self, booking: Booking) -> None:
        try:
            busy = json.loads(self.local_busy_path.read_text(encoding="utf-8"))
            busy = [b for b in busy if b.get("booking_id") != booking.id]
            self.local_busy_path.write_text(json.dumps(busy, indent=2), encoding="utf-8")
        except Exception:
            pass
        if self.backend == "google" and booking.calendar_event_id:
            self._google_delete(booking.calendar_event_id)

    def _google_busy(self) -> list[tuple[datetime, datetime]]:
        # Optional live freebusy — fails soft if not configured
        cal = self.cfg.get("calendar") or {}
        creds_path = Path(cal.get("google_credentials_path") or "credentials.json")
        token_path = Path(cal.get("google_token_path") or "token.json")
        if not token_path.exists() and not creds_path.exists():
            return []
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            if not token_path.exists():
                return []
            creds = Credentials.from_authorized_user_file(str(token_path))
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            now = datetime.now(timezone.utc)
            body = {
                "timeMin": now.isoformat(),
                "timeMax": (now + timedelta(days=14)).isoformat(),
                "items": [{"id": cal.get("google_calendar_id") or "primary"}],
            }
            fb = service.freebusy().query(body=body).execute()
            out: list[tuple[datetime, datetime]] = []
            cals = fb.get("calendars") or {}
            for blocks in cals.values():
                for b in blocks.get("busy") or []:
                    s = datetime.fromisoformat(b["start"].replace("Z", "+00:00"))
                    e = datetime.fromisoformat(b["end"].replace("Z", "+00:00"))
                    out.append((s, e))
            return out
        except Exception:
            return []

    def _google_create(self, booking: Booking) -> str | None:
        cal = self.cfg.get("calendar") or {}
        token_path = Path(cal.get("google_token_path") or "token.json")
        if not token_path.exists():
            return None
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials.from_authorized_user_file(str(token_path))
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            event = {
                "summary": f"{booking.service_name} — {booking.customer.name or 'Guest'}",
                "description": booking.notes or "",
                "start": {"dateTime": booking.start_iso, "timeZone": booking.timezone},
                "end": {"dateTime": booking.end_iso, "timeZone": booking.timezone},
                "attendees": (
                    [{"email": booking.customer.email}] if booking.customer.email else []
                ),
            }
            created = (
                service.events()
                .insert(
                    calendarId=cal.get("google_calendar_id") or "primary",
                    body=event,
                    sendUpdates="all" if booking.customer.email else "none",
                )
                .execute()
            )
            return created.get("id")
        except Exception:
            return None

    def _google_delete(self, event_id: str) -> None:
        cal = self.cfg.get("calendar") or {}
        token_path = Path(cal.get("google_token_path") or "token.json")
        if not token_path.exists():
            return
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials.from_authorized_user_file(str(token_path))
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            service.events().delete(
                calendarId=cal.get("google_calendar_id") or "primary",
                eventId=event_id,
            ).execute()
        except Exception:
            pass

    def calendly_available(self) -> bool:
        cal = self.cfg.get("calendar") or {}
        return bool(cal.get("calendly_token") and cal.get("calendly_event_type_uri"))

    def calendly_list_event_types(self) -> dict[str, Any]:
        """Calendly-style API example call (optional)."""
        cal = self.cfg.get("calendar") or {}
        token = cal.get("calendly_token") or ""
        if not token:
            return {"ok": False, "reason": "not configured"}
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    "https://api.calendly.com/event_types",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if not resp.is_success:
                    return {"ok": False, "status": resp.status_code}
                return {"ok": True, "data": resp.json()}
        except Exception as e:
            return {"ok": False, "reason": str(e)}
