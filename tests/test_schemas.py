from datetime import datetime, timezone
from collector.schemas import Account, Post


def _make_post(**overrides):
    base = dict(
        platform="bilibili",
        post_id="BV1xx",
        url="https://www.bilibili.com/video/BV1xx",
        title="标题",
        caption=None,
        cover_url="https://i0.hdslb.com/cover.jpg",
        duration_sec=120,
        media_type="video",
        published_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        like_count=10,
        comment_count=2,
        share_count=1,
        view_count=300,
        collect_count=5,
        author_id="448167395",
        author_name="复旦大学",
        fetched_at=datetime(2026, 6, 8, 8, 0, tzinfo=timezone.utc),
        raw={"foo": "bar"},
    )
    base.update(overrides)
    return Post(**base)


def test_post_round_trip():
    p = _make_post()
    data = p.model_dump(mode="json")
    p2 = Post.model_validate(data)
    assert p2 == p


def test_extras_defaults_to_empty_dict():
    p = _make_post()
    assert p.extras == {}


def test_optional_metrics_default_to_none():
    p = _make_post(like_count=None, view_count=None)
    assert p.like_count is None
    assert p.view_count is None


def test_account_basic():
    a = Account(platform="bilibili", account_id="448167395", account_name="复旦大学")
    assert a.platform == "bilibili"
    assert a.account_id == "448167395"
