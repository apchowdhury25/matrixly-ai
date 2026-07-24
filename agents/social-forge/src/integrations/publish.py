"""Publish adapters: local log, Buffer, Meta Graph, LinkedIn stubs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from ..models import Campaign, PlatformPost, PostStatus, utc_now


class Publisher:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.cfg = cfg
        self.dir = Path(data_dir) / "publish"
        self.dir.mkdir(parents=True, exist_ok=True)

    def publish_campaign(
        self,
        campaign: Campaign,
        platforms: list[str] | None = None,
        backend: str | None = None,
    ) -> Campaign:
        backend = (backend or (self.cfg.get("publish") or {}).get("backend") or "local").lower()
        targets = platforms or list(campaign.posts.keys())
        for p in targets:
            post = campaign.posts.get(p)
            if not post:
                continue
            result = self._publish_one(p, post, campaign.id, backend)
            post.publish_result = result
            post.published_at = utc_now()
            post.status = PostStatus.published if result.get("ok") else PostStatus.failed
        return campaign

    def _publish_one(
        self,
        platform: str,
        post: PlatformPost,
        campaign_id: str,
        backend: str,
    ) -> dict[str, Any]:
        text = post.text
        if post.hashtags:
            tags = " ".join(post.hashtags)
            if tags not in text:
                text = f"{text}\n\n{tags}"

        if backend == "buffer":
            return self._buffer(platform, text, campaign_id)
        if backend == "meta":
            return self._meta(platform, text, campaign_id)
        if backend == "linkedin":
            return self._linkedin(text, campaign_id)
        return self._local(platform, text, campaign_id, backend)

    def _local(
        self, platform: str, text: str, campaign_id: str, backend: str
    ) -> dict[str, Any]:
        row = {
            "ok": True,
            "backend": backend or "local",
            "platform": platform,
            "campaign_id": campaign_id,
            "text": text,
            "ts": utc_now(),
            "note": "Logged locally — connect Buffer/Meta/LinkedIn for live publish.",
        }
        path = self.dir / f"{campaign_id}_{platform}_{utc_now().replace(':', '')[:15]}.json"
        path.write_text(json.dumps(row, indent=2), encoding="utf-8")
        row["path"] = str(path)
        return row

    def _buffer(self, platform: str, text: str, campaign_id: str) -> dict[str, Any]:
        buf = self.cfg.get("buffer") or {}
        token = buf.get("access_token")
        profiles = buf.get("profile_ids") or []
        if not token or not profiles:
            r = self._local(platform, text, campaign_id, "buffer")
            r["ok"] = True
            r["note"] = "BUFFER credentials missing — saved local stub."
            return r
        # Buffer API create update (simplified)
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.bufferapp.com/1/updates/create.json",
                    data={
                        "access_token": token,
                        "profile_ids[]": profiles[0],
                        "text": text,
                        "now": True,
                    },
                )
                ok = resp.status_code < 400
                return {
                    "ok": ok,
                    "backend": "buffer",
                    "platform": platform,
                    "status_code": resp.status_code,
                    "body": resp.text[:500],
                    "ts": utc_now(),
                }
        except Exception as e:
            r = self._local(platform, text, campaign_id, "buffer")
            r["ok"] = False
            r["error"] = str(e)
            return r

    def _meta(self, platform: str, text: str, campaign_id: str) -> dict[str, Any]:
        meta = self.cfg.get("meta") or {}
        token = meta.get("access_token")
        page_id = meta.get("page_id")
        ig = meta.get("ig_user_id")
        if not token:
            r = self._local(platform, text, campaign_id, "meta")
            r["note"] = "META credentials missing — saved local stub."
            return r
        try:
            with httpx.Client(timeout=30.0) as client:
                if platform == "instagram" and ig:
                    # Caption-only stub — media publish needs container workflow
                    return {
                        "ok": True,
                        "backend": "meta",
                        "platform": "instagram",
                        "note": "IG media container required for live; draft logged.",
                        "caption": text[:500],
                        "ts": utc_now(),
                    }
                if page_id:
                    resp = client.post(
                        f"https://graph.facebook.com/v19.0/{page_id}/feed",
                        params={"message": text, "access_token": token},
                    )
                    return {
                        "ok": resp.status_code < 400,
                        "backend": "meta",
                        "platform": platform,
                        "status_code": resp.status_code,
                        "body": resp.text[:500],
                        "ts": utc_now(),
                    }
        except Exception as e:
            r = self._local(platform, text, campaign_id, "meta")
            r["ok"] = False
            r["error"] = str(e)
            return r
        return self._local(platform, text, campaign_id, "meta")

    def _linkedin(self, text: str, campaign_id: str) -> dict[str, Any]:
        li = self.cfg.get("linkedin") or {}
        token = li.get("access_token")
        author = li.get("org_urn") or li.get("person_urn")
        if not token or not author:
            r = self._local("linkedin", text, campaign_id, "linkedin")
            r["note"] = "LINKEDIN credentials missing — saved local stub."
            return r
        body = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text[:3000]},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.linkedin.com/v2/ugcPosts",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                    json=body,
                )
                return {
                    "ok": resp.status_code < 400,
                    "backend": "linkedin",
                    "platform": "linkedin",
                    "status_code": resp.status_code,
                    "body": resp.text[:500],
                    "ts": utc_now(),
                }
        except Exception as e:
            r = self._local("linkedin", text, campaign_id, "linkedin")
            r["ok"] = False
            r["error"] = str(e)
            return r
