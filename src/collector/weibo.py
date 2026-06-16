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
_FEED_URL = "https://weibo.com/ajax/statuses/mymblog"


def _parse_weibo_time(s: str) -> datetime:
    return datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")


class Weibo:
    name = "weibo"

    def fetch_user_feed(
        self, account: Account, cookies: dict[str, str], since_post_id: str | None
    ) -> Iterator[RawPost]:
        headers = {
            "User-Agent": _UA,
            "Referer": f"https://weibo.com/u/{account.account_id}",
            "Accept": "application/json, text/plain, */*",
            "x-requested-with": "XMLHttpRequest",
            "x-xsrf-token": cookies.get("XSRF-TOKEN", ""),
        }
        self.last_response = {}
        with httpx.Client(cookies=cookies, headers=headers) as client:
            page = 1
            while True:
                r = client.get(
                    _FEED_URL,
                    params={"uid": account.account_id, "page": page, "feature": 0},
                    timeout=15,
                )
                data = r.json()
                self.last_response = data  # cookie_health 读顶层 ok
                if not data.get("ok"):
                    logger.warning("weibo not ok page={} data={}", page, data)
                    return
                items = data["data"]["list"]
                if not items:
                    return
                for item in items:
                    yield RawPost(account=account, raw=item, post_id=item["mblogid"])
                page += 1
                time.sleep(2)

    def parse(self, raw: RawPost, account: Account) -> Post:
        item = raw.raw
        pic_urls = "|".join(
            v["large"]["url"] for v in (item.get("pic_infos") or {}).values()
        )
        video_url = (
            (item.get("page_info") or {}).get("media_info", {}).get("stream_url") or ""
        )
        text = item.get("text_raw", "")
        if item.get("pic_infos") and video_url:
            mtype = "mixed"
        elif video_url:
            mtype = "video"
        elif item.get("pic_infos"):
            mtype = "image"
        else:
            mtype = "text"
        user = item.get("user") or {}
        return Post(
            platform="weibo",
            post_id=item["mblogid"],
            url=f"https://weibo.com/{user.get('id', account.account_id)}/{item['mblogid']}",
            title=text,
            caption=None,
            cover_url=None,
            duration_sec=None,
            media_type=mtype,
            published_at=_parse_weibo_time(item["created_at"]),
            like_count=item.get("attitudes_count"),
            comment_count=item.get("comments_count"),
            share_count=item.get("reposts_count"),
            view_count=item.get("reads_count"),
            author_id=str(user.get("id", account.account_id)),
            author_name=user.get("screen_name", account.account_name),
            fetched_at=datetime.now(timezone.utc),
            raw=item,
            extras={"video_url": video_url, "image_urls": pic_urls},
        )

    def cookie_health(self, last_response: dict[str, Any]) -> CookieHealth:
        if last_response.get("ok") == 0:
            return "expired"
        return "ok"
