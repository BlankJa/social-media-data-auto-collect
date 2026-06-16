from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Iterator

import httpx
from loguru import logger

from collector.base import CookieHealth
# 快手计数字段过万同样返回「121.7万」「1.2亿」中文串，复用 B 站的解析逻辑。
from collector.bilibili import _parse_count
from collector.schemas import Account, Post, RawPost


_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_GQL = "https://www.kuaishou.com/graphql"


# 真机实测（2026-06-16）：photo 是接口类型 Photo，需 `... on PhotoEntity` 内联片段；
# Photo 上没有 shareCount（commentCount 在 PhotoEntity 上恒为 null）。
# likeCount/viewCount 以字符串数字返回（parse 时 pydantic 自动转 int），duration/timestamp 为毫秒。
_QUERY = """
query visionProfilePhotoList($pcursor: String, $userId: String, $page: String, $webPageArea: String) {
  visionProfilePhotoList(pcursor: $pcursor, userId: $userId, page: $page, webPageArea: $webPageArea) {
    result
    pcursor
    feeds {
      type
      author { id name }
      photo {
        __typename
        ... on PhotoEntity {
          id
          duration
          caption
          coverUrl
          photoUrl
          likeCount
          commentCount
          viewCount
          realLikeCount
          timestamp
        }
      }
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
        self.last_response = {}
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
                # result 在 vppl 内（非顶层），cookie_health 读它
                self.last_response = vppl
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
            like_count=_parse_count(photo.get("likeCount")),
            comment_count=_parse_count(photo.get("commentCount")),
            share_count=None,  # Photo 接口无 shareCount 字段
            view_count=_parse_count(photo.get("viewCount")),
            author_id=str(author.get("id", account.account_id)),
            author_name=author.get("name", account.account_name),
            fetched_at=datetime.now(timezone.utc),
            raw=f,
        )

    def cookie_health(self, last_response: dict[str, Any]) -> CookieHealth:
        # last_response 是 visionProfilePhotoList 节点。真机实测：result==1 是正常有数据，
        # result==2 是「翻到底」的正常结束信号（240 条采完那页就是 2），不能判过期。
        # 已知局限：快手 result 对「未登录/cookie 过期」与「正常翻完」可能都返回 2，
        # 无法仅凭响应区分，故这里不主动报 expired，避免每次跑完误报。
        result = last_response.get("result")
        if result not in (None, 1, 2):
            return "warning"
        return "ok"
