from datetime import datetime, timezone
from pathlib import Path

from collector.base import collect_account
from collector.schemas import Account, Post, RawPost


class FakePlatform:
    """按顺序返回 N 条 RawPost 的模拟平台。"""

    name = "bilibili"

    def __init__(self, posts: list[Post]):
        self._posts = posts
        self.health = "ok"

    def fetch_user_feed(self, account, cookies, since_post_id):
        for p in self._posts:
            yield RawPost(account=account, raw=p.raw, post_id=p.post_id)
            if since_post_id is not None and p.post_id == since_post_id:
                return

    def parse(self, raw, account):
        return next(p for p in self._posts if p.post_id == raw.post_id)

    def cookie_health(self, last_response):
        return self.health


def _post(post_id: str) -> Post:
    return Post(
        platform="bilibili",
        post_id=post_id,
        url=f"https://www.bilibili.com/video/{post_id}",
        title=post_id,
        media_type="video",
        published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        author_id="A1",
        author_name="复旦",
        fetched_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        raw={"id": post_id},
    )


def test_full_run_saves_all(tmp_path: Path):
    plat = FakePlatform([_post("BV3"), _post("BV2"), _post("BV1")])
    account = Account(platform="bilibili", account_id="A1", account_name="复旦")
    result = collect_account(plat, account, cookies={}, data_root=tmp_path, full=True)
    assert result.new_posts == 3
    assert (tmp_path / "bilibili" / "A1" / "BV1.json").exists()
    assert (tmp_path / "bilibili" / "A1" / "BV3.json").exists()


def test_incremental_stops_at_watermark(tmp_path: Path):
    plat = FakePlatform([_post("BV3"), _post("BV2"), _post("BV1")])
    account = Account(platform="bilibili", account_id="A1", account_name="复旦")
    collect_account(plat, account, cookies={}, data_root=tmp_path, full=True)

    # 新一条 BV4 出现在最前
    plat2 = FakePlatform([_post("BV4"), _post("BV3"), _post("BV2"), _post("BV1")])
    result = collect_account(plat2, account, cookies={}, data_root=tmp_path, full=False)
    assert result.new_posts == 1
    assert result.stopped_at == "BV3"
