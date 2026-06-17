"""锁住 cli.render 的「选哪些帖子」逻辑——此前无测试覆盖，藏了两个 bug：
① 只渲 fetched_at==渲染日 的帖子 → 增量后第二天起导不出完整主页；
② 把已从 config 移除但数据残留的旧账号目录也渲进去。
见 commit c0f80b4。"""

import json
from datetime import datetime, timezone
from pathlib import Path

from cli import select_render_posts
from collector.schemas import Account, Post


def _post(post_id: str, account_id: str, fetched: datetime) -> dict:
    return Post(
        platform="bilibili",
        post_id=post_id,
        url=f"https://www.bilibili.com/video/{post_id}",
        title="某视频",
        caption="简介",
        cover_url="https://i0.hdslb.com/cover.jpg",
        duration_sec=120,
        media_type="video",
        published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        like_count=1,
        comment_count=1,
        share_count=1,
        view_count=1,
        author_id=account_id,
        author_name="某博主",
        fetched_at=fetched,
        raw={},
    ).model_dump(mode="json")


def _write(data_root: Path, platform: str, account_id: str, post: dict) -> None:
    acc_dir = data_root / platform / account_id
    acc_dir.mkdir(parents=True, exist_ok=True)
    (acc_dir / f"{post['post_id']}.json").write_text(
        json.dumps(post), encoding="utf-8"
    )


def _account(account_id: str) -> Account:
    return Account(platform="bilibili", account_id=account_id, account_name="某博主")


def test_renders_full_snapshot_regardless_of_fetch_date(tmp_path: Path):
    """全量快照：老帖（fetched_at 是几天前）也要渲进来，不只渲当天采的。"""
    old = datetime(2026, 6, 8, tzinfo=timezone.utc)
    today = datetime(2026, 6, 17, tzinfo=timezone.utc)
    _write(tmp_path, "bilibili", "A1", _post("BV_old1", "A1", old))
    _write(tmp_path, "bilibili", "A1", _post("BV_old2", "A1", old))
    _write(tmp_path, "bilibili", "A1", _post("BV_new", "A1", today))

    posts = select_render_posts("bilibili", tmp_path, [_account("A1")])

    assert {p.post_id for p in posts} == {"BV_old1", "BV_old2", "BV_new"}


def test_only_includes_accounts_in_config(tmp_path: Path):
    """盘上残留的旧账号目录（已从 config 移除）不进结果。"""
    now = datetime(2026, 6, 17, tzinfo=timezone.utc)
    _write(tmp_path, "bilibili", "kept", _post("BV_kept", "kept", now))
    _write(tmp_path, "bilibili", "orphan", _post("BV_orphan", "orphan", now))

    posts = select_render_posts("bilibili", tmp_path, [_account("kept")])

    assert [p.post_id for p in posts] == ["BV_kept"]


def test_skips_meta_json(tmp_path: Path):
    """_meta.json 不是帖子，不能被当成 Post 渲进去。"""
    now = datetime(2026, 6, 17, tzinfo=timezone.utc)
    _write(tmp_path, "bilibili", "A1", _post("BV1", "A1", now))
    (tmp_path / "bilibili" / "A1" / "_meta.json").write_text(
        json.dumps({"account_id": "A1", "total_posts": 1}), encoding="utf-8"
    )

    posts = select_render_posts("bilibili", tmp_path, [_account("A1")])

    assert [p.post_id for p in posts] == ["BV1"]


def test_missing_platform_dir_returns_empty(tmp_path: Path):
    assert select_render_posts("bilibili", tmp_path, [_account("A1")]) == []
