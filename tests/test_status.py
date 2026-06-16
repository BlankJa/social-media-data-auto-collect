from datetime import datetime, timezone
from pathlib import Path

from collector.cookies import save_cookies
from collector.status import (
    PlatformStatus,
    RunStatus,
    cookie_advice,
    count_recent_posts,
    read_status,
    write_status,
)


def test_cookie_advice_missing(tmp_path: Path):
    age, advice = cookie_advice("kuaishou", tmp_path / "nope.json", None)
    assert age == "—"
    assert "未登录" in advice


def test_cookie_advice_expired(tmp_path: Path):
    p = tmp_path / "weibo.json"
    save_cookies(p, platform="weibo", cookies=[{"name": "a", "value": "1"}])
    age, advice = cookie_advice("weibo", p, "expired")
    assert "已过期" in advice


def test_cookie_advice_fresh_ok(tmp_path: Path):
    p = tmp_path / "bilibili.json"
    save_cookies(p, platform="bilibili", cookies=[{"name": "a", "value": "1"}])
    age, advice = cookie_advice("bilibili", p, "ok")
    assert advice.startswith("✅")
    assert age == "0天"


def test_write_then_read(tmp_path: Path):
    p = tmp_path / "status.json"
    rs = RunStatus(
        last_run_started_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        last_run_finished_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        last_run_mode="incremental",
        platforms={
            "bilibili": PlatformStatus(
                accounts_total=2,
                accounts_ok=2,
                accounts_failed=0,
                new_posts=3,
                new_posts_7d=10,
                cookie_health="ok",
            )
        },
    )
    write_status(p, rs)
    assert read_status(p) == rs


def test_count_recent_posts(tmp_path: Path):
    # 构造两个文件，fetched_at 一个在 7 天内、一个在外
    (tmp_path / "bilibili" / "A1").mkdir(parents=True)
    (tmp_path / "bilibili" / "A1" / "BV1.json").write_text(
        '{"fetched_at": "%s"}' % datetime.now(timezone.utc).isoformat(), "utf-8"
    )
    (tmp_path / "bilibili" / "A1" / "BV2.json").write_text(
        '{"fetched_at": "2020-01-01T00:00:00+00:00"}', "utf-8"
    )
    assert count_recent_posts(tmp_path, "bilibili", days=7) == 1


def test_count_recent_posts_skips_meta(tmp_path: Path):
    """_meta.json 不是帖子，不应计入。"""
    (tmp_path / "bilibili" / "A1").mkdir(parents=True)
    (tmp_path / "bilibili" / "A1" / "_meta.json").write_text(
        '{"fetched_at": "%s"}' % datetime.now(timezone.utc).isoformat(), "utf-8"
    )
    assert count_recent_posts(tmp_path, "bilibili", days=7) == 0
