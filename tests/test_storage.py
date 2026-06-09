import json
from datetime import datetime, timezone
from pathlib import Path

from collector.schemas import Post
from collector.storage import (
    Meta,
    is_saved,
    load_meta,
    post_path,
    save_meta,
    save_post,
)


def _post(post_id: str = "BV1") -> Post:
    return Post(
        platform="bilibili",
        post_id=post_id,
        url=f"https://www.bilibili.com/video/{post_id}",
        title="t",
        media_type="video",
        published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        author_id="A1",
        author_name="复旦",
        fetched_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        raw={"x": 1},
    )


def test_save_and_path(tmp_path: Path):
    p = _post("BV1")
    save_post(tmp_path, p)
    assert post_path(tmp_path, p.platform, p.author_id, p.post_id).exists()


def test_is_saved(tmp_path: Path):
    p = _post("BV1")
    assert not is_saved(tmp_path, p.platform, p.author_id, p.post_id)
    save_post(tmp_path, p)
    assert is_saved(tmp_path, p.platform, p.author_id, p.post_id)


def test_overwrite_is_atomic(tmp_path: Path):
    p1 = _post("BV1")
    save_post(tmp_path, p1)
    p2 = p1.model_copy(update={"title": "更新后"})
    save_post(tmp_path, p2)
    data = json.loads(post_path(tmp_path, "bilibili", "A1", "BV1").read_text("utf-8"))
    assert data["title"] == "更新后"


def test_meta_round_trip(tmp_path: Path):
    m = Meta(
        account_id="A1",
        account_name="复旦",
        last_run_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        last_run_mode="incremental",
        newest_post_id="BV1",
        total_posts=1,
        last_error=None,
    )
    save_meta(tmp_path, "bilibili", "A1", m)
    m2 = load_meta(tmp_path, "bilibili", "A1")
    assert m2 == m


def test_load_meta_missing_returns_none(tmp_path: Path):
    assert load_meta(tmp_path, "bilibili", "A1") is None
