from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Iterator

import httpx
from loguru import logger

from collector.base import CookieHealth
from collector.schemas import Account, Post, RawPost
from collector.signing.douyin_abogus import sign_params


_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_FEED_URL = "https://www.douyin.com/aweme/v1/web/aweme/post/"


class Douyin:
    name = "douyin"

    def fetch_user_feed(
        self, account: Account, cookies: dict[str, str], since_post_id: str | None
    ) -> Iterator[RawPost]:
        headers = {
            "User-Agent": _UA,
            "Referer": f"https://www.douyin.com/user/{account.account_id}",
        }
        with httpx.Client(cookies=cookies, headers=headers, http2=True) as client:
            max_cursor = 0
            while True:
                params = sign_params(
                    {
                        "device_platform": "webapp",
                        "aid": "6383",
                        "channel": "channel_pc_web",
                        "sec_user_id": account.account_id,
                        "count": "18",
                        "max_cursor": str(max_cursor),
                        "cookie_enabled": "true",
                        "platform": "PC",
                    },
                    _UA,
                )
                r = client.get(_FEED_URL, params=params, timeout=15)
                data = r.json()
                if data.get("status_code") not in (None, 0):
                    logger.warning(
                        "douyin code={} msg={}",
                        data.get("status_code"),
                        data.get("status_msg"),
                    )
                    return
                items = data.get("aweme_list") or []
                for item in items:
                    yield RawPost(account=account, raw=item, post_id=item["aweme_id"])
                if not data.get("has_more"):
                    return
                max_cursor = data.get("max_cursor", 0)
                time.sleep(2)

    def parse(self, raw: RawPost, account: Account) -> Post:
        item = raw.raw
        s = item.get("statistics", {})
        v = item.get("video", {})
        author = item.get("author", {})
        cover = (v.get("cover") or {}).get("url_list") or []
        return Post(
            platform="douyin",
            post_id=item["aweme_id"],
            url=f"https://www.douyin.com/video/{item['aweme_id']}",
            title=item.get("desc", ""),
            caption=None,
            cover_url=cover[0] if cover else None,
            duration_sec=int(v.get("duration", 0) / 1000) or None,
            media_type="video",
            published_at=datetime.fromtimestamp(item["create_time"], tz=timezone.utc),
            like_count=s.get("digg_count"),
            comment_count=s.get("comment_count"),
            share_count=s.get("share_count"),
            view_count=s.get("play_count"),
            collect_count=s.get("collect_count"),
            author_id=author.get("sec_uid", account.account_id),
            author_name=author.get("nickname", account.account_name),
            fetched_at=datetime.now(timezone.utc),
            raw=item,
            extras={"author_bio": author.get("signature", "")},
        )

    def cookie_health(self, last_response: dict[str, Any]) -> CookieHealth:
        sc = last_response.get("status_code")
        if sc in (100002, 8, 2154):
            return "expired"
        if sc not in (None, 0):
            return "warning"
        return "ok"
