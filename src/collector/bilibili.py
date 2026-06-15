from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Iterator

import httpx
from loguru import logger

from collector.base import CookieHealth
from collector.schemas import Account, Post, RawPost
from collector.signing.bilibili_wbi import compute_mixin_key, sign_params


_NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
_FEED_URL = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)


def _parse_count(value: object) -> int | None:
    """B 站计数字段过万会返回「5.6万」「1.2亿」这类字符串，统一转 int。"""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if s.endswith("万"):
        return int(float(s[:-1]) * 10_000)
    if s.endswith("亿"):
        return int(float(s[:-1]) * 100_000_000)
    return int(s)


def _duration_text_to_sec(text: str | None) -> int | None:
    if not text:
        return None
    parts = [int(p) for p in text.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return None


class Bilibili:
    name = "bilibili"

    def _get_mixin_key(self, client: httpx.Client) -> str:
        r = client.get(_NAV_URL, timeout=10)
        wbi = r.json()["data"]["wbi_img"]
        img_key = wbi["img_url"].rsplit("/", 1)[-1].split(".")[0]
        sub_key = wbi["sub_url"].rsplit("/", 1)[-1].split(".")[0]
        return compute_mixin_key(img_key, sub_key)

    def fetch_user_feed(
        self, account: Account, cookies: dict[str, str], since_post_id: str | None
    ) -> Iterator[RawPost]:
        headers = {
            "User-Agent": _UA,
            "Referer": f"https://space.bilibili.com/{account.account_id}/dynamic",
        }
        with httpx.Client(cookies=cookies, headers=headers, http2=True) as client:
            mixin = self._get_mixin_key(client)
            offset = ""
            while True:
                params = sign_params(
                    {
                        "offset": offset,
                        "host_mid": account.account_id,
                        "timezone_offset": "-480",
                        "platform": "web",
                        "features": "itemOpusStyle",
                        "web_location": "333.1387",
                    },
                    mixin_key=mixin,
                    wts=int(time.time()),
                )
                r = client.get(_FEED_URL, params=params, timeout=15)
                data = r.json()
                if data.get("code") != 0:
                    logger.warning(
                        "bilibili feed code={} msg={}",
                        data.get("code"),
                        data.get("message"),
                    )
                    return
                items = data["data"]["items"]
                for item in items:
                    major = item["modules"]["module_dynamic"].get("major") or {}
                    archive = major.get("archive")
                    if not archive:
                        # 非视频动态（转发、图文等）跳过
                        continue
                    yield RawPost(account=account, raw=item, post_id=archive["bvid"])
                if not data["data"].get("has_more"):
                    return
                offset = data["data"]["offset"]
                time.sleep(2)

    def parse(self, raw: RawPost, account: Account) -> Post:
        item = raw.raw
        archive = item["modules"]["module_dynamic"]["major"]["archive"]
        stat = item["modules"]["module_stat"]
        author = item["modules"]["module_author"]

        return Post(
            platform="bilibili",
            post_id=archive["bvid"],
            url=f"https://www.bilibili.com/video/{archive['bvid']}",
            title=archive["title"],
            caption=archive.get("desc"),
            cover_url=archive.get("cover"),
            duration_sec=_duration_text_to_sec(archive.get("duration_text")),
            media_type="video",
            published_at=datetime.fromtimestamp(int(author["pub_ts"]), tz=timezone.utc),
            like_count=_parse_count(stat.get("like", {}).get("count")),
            comment_count=_parse_count(stat.get("comment", {}).get("count")),
            share_count=_parse_count(stat.get("forward", {}).get("count")),
            view_count=_parse_count(archive.get("stat", {}).get("play")),
            collect_count=None,
            author_id=str(author["mid"]),
            author_name=author["name"],
            fetched_at=datetime.now(timezone.utc),
            raw=item,
        )

    def cookie_health(self, last_response: dict[str, Any]) -> CookieHealth:
        code = last_response.get("code")
        if code in (-101, -111, -400):
            return "expired"
        if code != 0:
            return "warning"
        return "ok"
