"""Persistent booking store + CRM-lite sync."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models import Booking, BookingStatus, Customer, new_id, utc_now


class BookingStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "bookings"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.crm_path = Path(data_dir) / "crm" / "contacts.json"
        self.crm_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_path = Path(data_dir) / "crm" / "contacts.csv"

    def _path(self, booking_id: str) -> Path:
        return self.dir / f"{booking_id}.json"

    def create(self, booking: Booking) -> Booking:
        if not booking.id:
            booking.id = new_id("bk_")
        self.save(booking)
        self._upsert_crm(booking.customer)
        return booking

    def save(self, booking: Booking) -> None:
        booking.updated_at = utc_now()
        with self._path(booking.id).open("w", encoding="utf-8") as f:
            json.dump(booking.model_dump(), f, indent=2, ensure_ascii=False)

    def get(self, booking_id: str) -> Booking | None:
        p = self._path(booking_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return Booking(**json.load(f))

    def list(
        self,
        status: str | None = None,
        upcoming_only: bool = False,
        limit: int = 100,
    ) -> list[Booking]:
        items: list[Booking] = []
        now = datetime.now(timezone.utc)
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                with p.open(encoding="utf-8") as f:
                    b = Booking(**json.load(f))
            except Exception:
                continue
            if status and b.status.value != status:
                continue
            if upcoming_only:
                if b.status not in {BookingStatus.confirmed, BookingStatus.pending_hitl}:
                    continue
                try:
                    start = datetime.fromisoformat(b.start_iso.replace("Z", "+00:00"))
                    if start.tzinfo is None:
                        start = start.replace(tzinfo=timezone.utc)
                    if start < now:
                        continue
                except Exception:
                    continue
            items.append(b)
            if len(items) >= limit:
                break
        # Sort upcoming by start time ascending
        if upcoming_only:
            items.sort(key=lambda x: x.start_iso)
        return items

    def find_by_email(self, email: str) -> list[Booking]:
        email = (email or "").lower()
        return [
            b
            for b in self.list(limit=200)
            if (b.customer.email or "").lower() == email
            and b.status == BookingStatus.confirmed
        ]

    def cancel(self, booking_id: str, reason: str = "") -> Booking | None:
        b = self.get(booking_id)
        if not b:
            return None
        b.status = BookingStatus.cancelled
        b.metadata["cancel_reason"] = reason
        self.save(b)
        return b

    def busy_intervals(self) -> list[tuple[datetime, datetime]]:
        out: list[tuple[datetime, datetime]] = []
        for b in self.list(limit=500):
            if b.status not in {BookingStatus.confirmed, BookingStatus.pending_hitl}:
                continue
            try:
                s = datetime.fromisoformat(b.start_iso.replace("Z", "+00:00"))
                e = datetime.fromisoformat(b.end_iso.replace("Z", "+00:00"))
                if s.tzinfo is None:
                    s = s.replace(tzinfo=timezone.utc)
                if e.tzinfo is None:
                    e = e.replace(tzinfo=timezone.utc)
                out.append((s, e))
            except Exception:
                continue
        return out

    def _upsert_crm(self, customer: Customer) -> None:
        if not customer.email and not customer.name:
            return
        contacts: list[dict[str, Any]] = []
        if self.crm_path.exists():
            try:
                contacts = json.loads(self.crm_path.read_text(encoding="utf-8"))
            except Exception:
                contacts = []
        email = (customer.email or "").lower()
        found = False
        for c in contacts:
            if email and (c.get("email") or "").lower() == email:
                c.update({k: v for k, v in customer.model_dump().items() if v})
                c["updated_at"] = utc_now()
                found = True
                break
        if not found:
            row = customer.model_dump()
            row["updated_at"] = utc_now()
            contacts.append(row)
        self.crm_path.write_text(
            json.dumps(contacts, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        with self.csv_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f, fieldnames=["name", "email", "phone", "timezone", "updated_at"]
            )
            w.writeheader()
            for c in contacts:
                w.writerow({k: c.get(k, "") for k in w.fieldnames})
