from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from collector.schemas import Platform, Post


class Meta(BaseModel):
    account_id: str
    account_name: str
    last_run_at: datetime
    last_run_mode: Literal["incremental", "full"]
    newest_post_id: str | None
    total_posts: int
    last_error: str | None = None


def account_dir(data_root: Path, platform: Platform, account_id: str) -> Path:
    return data_root / platform / account_id


def post_path(data_root: Path, platform: Platform, account_id: str, post_id: str) -> Path:
    return account_dir(data_root, platform, account_id) / f"{post_id}.json"


def meta_path(data_root: Path, platform: Platform, account_id: str) -> Path:
    return account_dir(data_root, platform, account_id) / "_meta.json"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def save_post(data_root: Path, post: Post) -> None:
    _atomic_write(
        post_path(data_root, post.platform, post.author_id, post.post_id),
        post.model_dump_json(indent=2),
    )


def is_saved(data_root: Path, platform: Platform, account_id: str, post_id: str) -> bool:
    return post_path(data_root, platform, account_id, post_id).exists()


def save_meta(data_root: Path, platform: Platform, account_id: str, meta: Meta) -> None:
    _atomic_write(
        meta_path(data_root, platform, account_id),
        meta.model_dump_json(indent=2),
    )


def load_meta(data_root: Path, platform: Platform, account_id: str) -> Meta | None:
    p = meta_path(data_root, platform, account_id)
    if not p.exists():
        return None
    return Meta.model_validate_json(p.read_text(encoding="utf-8"))
