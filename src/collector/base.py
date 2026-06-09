from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal, Protocol

from loguru import logger

from collector.schemas import Account, Platform as PlatformName, Post, RawPost
from collector.storage import Meta, is_saved, load_meta, save_meta, save_post


CookieHealth = Literal["ok", "warning", "expired"]


class Platform(Protocol):
    name: PlatformName

    def fetch_user_feed(
        self, account: Account, cookies: dict[str, str], since_post_id: str | None
    ) -> Iterator[RawPost]: ...

    def parse(self, raw: RawPost, account: Account) -> Post: ...

    def cookie_health(self, last_response: dict[str, Any]) -> CookieHealth: ...


@dataclass
class CollectResult:
    new_posts: int
    stopped_at: str | None
    cookie_health: CookieHealth
    error: str | None = None


def collect_account(
    platform: Platform,
    account: Account,
    cookies: dict[str, str],
    data_root: Path,
    *,
    full: bool = False,
) -> CollectResult:
    prev_meta = load_meta(data_root, platform.name, account.account_id)
    since = None if full else (prev_meta.newest_post_id if prev_meta else None)

    new_count = 0
    newest_seen: str | None = None
    stopped_at: str | None = None
    error: str | None = None
    health: CookieHealth = "ok"

    try:
        for raw in platform.fetch_user_feed(account, cookies, since_post_id=since):
            if newest_seen is None:
                newest_seen = raw.post_id

            if not full and is_saved(data_root, platform.name, account.account_id, raw.post_id):
                stopped_at = raw.post_id
                break

            post = platform.parse(raw, account)
            post = post.model_copy(update={"fetched_at": datetime.now(timezone.utc)})
            save_post(data_root, post)
            new_count += 1

            time.sleep(random.uniform(1.0, 3.0))
    except Exception as exc:
        error = repr(exc)
        logger.exception(
            "collect_account failed for {} / {}", platform.name, account.account_id
        )

    save_meta(
        data_root,
        platform.name,
        account.account_id,
        Meta(
            account_id=account.account_id,
            account_name=account.account_name,
            last_run_at=datetime.now(timezone.utc),
            last_run_mode="full" if full else "incremental",
            newest_post_id=newest_seen or (prev_meta.newest_post_id if prev_meta else None),
            total_posts=(prev_meta.total_posts if prev_meta else 0) + new_count,
            last_error=error,
        ),
    )

    return CollectResult(
        new_posts=new_count, stopped_at=stopped_at, cookie_health=health, error=error
    )
