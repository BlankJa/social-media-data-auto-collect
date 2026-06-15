from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Iterator

import httpx
from loguru import logger

from collector.base import CookieHealth
from collector.schemas import Account, Post, RawPost


_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_GQL = "https://www.kuaishou.com/graphql"


_QUERY = """
query visionProfilePhotoList($pcursor: String, $userId: String, $page: String, $webPageArea: String) {
  visionProfilePhotoList(pcursor: $pcursor, userId: $userId, page: $page, webPageArea: $webPageArea) {
    pcursor
    feeds {
      photo { id duration caption photoUrl coverUrl likeCount commentCount viewCount shareCount timestamp }
      author { id name }
    }
  }
}
"""


class Kuaishou:
    name = "kuaishou"

    def fetch_user_feed(
        self, account: Account, cookies: dict[str, str], since_post_id: str | None
    ) -> Iterator[RawPost]:
        headers = {
            "User-Agent": _UA,
            "Referer": f"https://www.kuaishou.com/profile/{account.account_id}",
            "Content-Type": "application/json",
        }
        with httpx.Client(cookies=cookies, headers=headers) as client:
            pcursor = ""
            while True:
                body = {
                    "operationName": "visionProfilePhotoList",
                    "query": _QUERY,
                    "variables": {
                        "pcursor": pcursor,
                        "userId": account.account_id,
                        "page": "profile",
                    },
                }
                r = client.post(_GQL, json=body, timeout=15)
                data = r.json()
                vppl = ((data.get("data") or {}).get("visionProfilePhotoList")) or {}
                feeds = vppl.get("feeds") or []
                if not feeds:
                    logger.warning("kuaishou empty feeds data={}", data)
                    return
                for f in feeds:
                    yield RawPost(account=account, raw=f, post_id=f["photo"]["id"])
                pcursor = vppl.get("pcursor")
                if not pcursor or pcursor == "no_more":
                    return
                time.sleep(2)

    def parse(self, raw: RawPost, account: Account) -> Post:
        f = raw.raw
        photo = f["photo"]
        author = f.get("author") or {}
        return Post(
            platform="kuaishou",
            post_id=photo["id"],
            url=f"https://www.kuaishou.com/short-video/{photo['id']}",
            title=photo.get("caption", ""),
            caption=None,
            cover_url=photo.get("coverUrl"),
            duration_sec=int(photo.get("duration", 0) / 1000) or None,
            media_type="video",
            published_at=datetime.fromtimestamp(photo["timestamp"] / 1000, tz=timezone.utc),
            like_count=photo.get("likeCount"),
            comment_count=photo.get("commentCount"),
            share_count=photo.get("shareCount"),
            view_count=photo.get("viewCount"),
            author_id=str(author.get("id", account.account_id)),
            author_name=author.get("name", account.account_name),
            fetched_at=datetime.now(timezone.utc),
            raw=f,
        )

    def cookie_health(self, last_response: dict[str, Any]) -> CookieHealth:
        result = last_response.get("result")
        if result == 2:
            return "expired"
        if result not in (None, 1):
            return "warning"
        return "ok"
