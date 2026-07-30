"""Publish/export to local files, Buffer, Hootsuite, or WordPress."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from ..models import SeoJob, utc_now


class Publisher:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.backend = ((cfg.get("publish") or {}).get("backend") or "local").lower()
        self.outputs = Path(cfg["paths"]["outputs"])

    def publish(self, job: SeoJob, targets: list[str] | None = None) -> dict[str, Any]:
        targets = targets or [self.backend]
        results: list[dict[str, Any]] = []
        for t in targets:
            t = t.lower()
            if t == "buffer":
                results.append(self._buffer(job))
            elif t == "hootsuite":
                results.append(self._hootsuite(job))
            elif t == "wordpress":
                results.append(self._wordpress(job))
            else:
                results.append(self._local(job))
        ok_any = any(r.get("ok") for r in results)
        return {"ok": ok_any, "results": results}

    def _local(self, job: SeoJob) -> dict[str, Any]:
        path = self.outputs / job.id / "publish_manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        draft = job.draft or {}
        payload = {
            "job_id": job.id,
            "published_at": utc_now(),
            "backend": "local",
            "title": draft.get("title") or job.title,
            "content_type": job.content_type,
            "export_paths": job.export_paths,
            "note": "Local export only — no public publish without HITL + target backend.",
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"ok": True, "backend": "local", "path": str(path)}

    def _buffer(self, job: SeoJob) -> dict[str, Any]:
        buf = self.cfg.get("buffer") or {}
        token = buf.get("access_token") or ""
        profiles = buf.get("profile_ids") or []
        if not token or not profiles:
            r = self._local(job)
            r["note"] = "Buffer not configured; wrote local manifest"
            return r
        draft = job.draft or {}
        social = draft.get("social_variants") or {}
        text = social.get("linkedin") or draft.get("title") or ""
        try:
            with httpx.Client(timeout=30.0) as client:
                for pid in profiles[:3]:
                    resp = client.post(
                        "https://api.bufferapp.com/1/updates/create.json",
                        data={
                            "access_token": token,
                            "profile_ids[]": pid,
                            "text": str(text)[:2000],
                            "now": True,
                        },
                    )
                    if not resp.is_success:
                        return {
                            "ok": False,
                            "backend": "buffer",
                            "reason": f"HTTP {resp.status_code}",
                        }
            return {"ok": True, "backend": "buffer", "profiles": profiles[:3]}
        except Exception as e:
            return {"ok": False, "backend": "buffer", "reason": str(e)}

    def _hootsuite(self, job: SeoJob) -> dict[str, Any]:
        r = self._local(job)
        r["note"] = "Hootsuite stub — local manifest written"
        r["backend"] = "hootsuite_local"
        return r

    def _wordpress(self, job: SeoJob) -> dict[str, Any]:
        wp = self.cfg.get("wordpress") or {}
        site = wp.get("site_url") or ""
        user = wp.get("username") or ""
        password = wp.get("app_password") or ""
        if not site or not user or not password:
            r = self._local(job)
            r["note"] = "WordPress not configured; wrote local manifest"
            return r
        draft = job.draft or {}
        title = draft.get("title") or job.title or "Draft"
        body = draft.get("body_markdown") or ""
        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(
                    f"{site}/wp-json/wp/v2/posts",
                    auth=(user, password),
                    json={
                        "title": title,
                        "content": body,
                        "status": "draft",
                        "slug": draft.get("slug") or "",
                    },
                )
                if not resp.is_success:
                    return {
                        "ok": False,
                        "backend": "wordpress",
                        "reason": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    }
                data = resp.json()
            return {
                "ok": True,
                "backend": "wordpress",
                "post_id": data.get("id"),
                "status": "draft",
                "link": data.get("link"),
            }
        except Exception as e:
            return {"ok": False, "backend": "wordpress", "reason": str(e)}
