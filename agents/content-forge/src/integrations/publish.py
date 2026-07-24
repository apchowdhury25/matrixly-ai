"""Publish/export to local files, Buffer, Hootsuite, or WordPress."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from ..models import ContentJob, utc_now


class Publisher:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.backend = ((cfg.get("publish") or {}).get("backend") or "local").lower()
        self.outputs = Path(cfg["paths"]["outputs"])

    def publish(self, job: ContentJob, targets: list[str] | None = None) -> dict[str, Any]:
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

    def _local(self, job: ContentJob) -> dict[str, Any]:
        path = self.outputs / job.id / "publish_manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "job_id": job.id,
            "published_at": utc_now(),
            "backend": "local",
            "title": (job.edited or job.draft or {}).get("title"),
            "assets": list((job.assets or {}).keys()),
            "export_paths": job.export_paths,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"ok": True, "backend": "local", "path": str(path)}

    def _buffer(self, job: ContentJob) -> dict[str, Any]:
        buf = self.cfg.get("buffer") or {}
        token = buf.get("access_token") or ""
        profiles = buf.get("profile_ids") or []
        if not token or not profiles:
            r = self._local(job)
            r["note"] = "Buffer not configured; wrote local manifest"
            r["backend"] = "local"
            return r
        text = (job.assets or {}).get("linkedin") or (job.edited or {}).get("title") or ""
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

    def _hootsuite(self, job: ContentJob) -> dict[str, Any]:
        token = (self.cfg.get("hootsuite") or {}).get("access_token") or ""
        if not token:
            r = self._local(job)
            r["note"] = "Hootsuite not configured; wrote local manifest"
            r["backend"] = "local"
            return r
        # Placeholder REST shape — soft fail to local
        text = (job.assets or {}).get("linkedin") or ""
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://platform.hootsuite.com/v1/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"text": str(text)[:2000]},
                )
                if not resp.is_success:
                    r = self._local(job)
                    r["note"] = f"Hootsuite HTTP {resp.status_code}; local fallback"
                    return r
            return {"ok": True, "backend": "hootsuite"}
        except Exception as e:
            r = self._local(job)
            r["note"] = str(e)
            return r

    def _wordpress(self, job: ContentJob) -> dict[str, Any]:
        wp = self.cfg.get("wordpress") or {}
        site = wp.get("site_url") or ""
        user = wp.get("username") or ""
        password = wp.get("app_password") or ""
        if not (site and user and password):
            r = self._local(job)
            r["note"] = "WordPress not configured; wrote local manifest"
            r["backend"] = "local"
            return r
        edited = job.edited or job.draft or {}
        payload = {
            "title": edited.get("title") or "Matrixly post",
            "content": edited.get("body_markdown") or "",
            "status": "draft",
            "slug": edited.get("slug") or "",
        }
        try:
            with httpx.Client(timeout=40.0) as client:
                resp = client.post(
                    f"{site}/wp-json/wp/v2/posts",
                    json=payload,
                    auth=(user, password),
                )
                if not resp.is_success:
                    return {
                        "ok": False,
                        "backend": "wordpress",
                        "reason": f"HTTP {resp.status_code}",
                    }
                data = resp.json()
                return {
                    "ok": True,
                    "backend": "wordpress",
                    "post_id": data.get("id"),
                    "link": data.get("link"),
                }
        except Exception as e:
            return {"ok": False, "backend": "wordpress", "reason": str(e)}
