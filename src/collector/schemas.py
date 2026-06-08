from __future__ import annotations
from datetime import datetime
from typing import Any, Callable, Literal
from pydantic import BaseModel, Field

Platform = Literal["bilibili", "weibo", "douyin", "kuaishou"]
MediaType = Literal["video", "image", "text", "mixed"]


class Account(BaseModel):
    platform: Platform
    account_id: str
    account_name: str


class RawPost(BaseModel):
    """平台子类 fetch_user_feed() 产出的中间态：原始接口字段 + 所属账号。"""

    account: Account
    raw: dict[str, Any]
    post_id: str


class Post(BaseModel):
    platform: Platform
    post_id: str
    url: str

    title: str
    caption: str | None = None
    cover_url: str | None = None
    duration_sec: int | None = None
    media_type: MediaType
    published_at: datetime

    like_count: int | None = None
    comment_count: int | None = None
    share_count: int | None = None
    view_count: int | None = None
    collect_count: int | None = None

    author_id: str
    author_name: str

    fetched_at: datetime
    raw: dict[str, Any]
    extras: dict[str, str] = Field(default_factory=dict)


class ColumnSpec(BaseModel):
    name: str
    extract: Callable[[Post], Any]

    model_config = {"arbitrary_types_allowed": True}
