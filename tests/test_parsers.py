import json
from pathlib import Path

from collector.bilibili import Bilibili, _parse_count
from collector.schemas import Account, RawPost


def test_parse_count_handles_units():
    assert _parse_count(656) == 656
    assert _parse_count("656") == 656
    assert _parse_count("5.6万") == 56000
    assert _parse_count("1.2亿") == 120000000
    assert _parse_count("") is None
    assert _parse_count(None) is None


def _load(name: str) -> dict:
    return json.loads(Path(f"tests/fixtures/{name}").read_text("utf-8"))


def test_bilibili_parse():
    sample = _load("bilibili/sample_response.json")
    item = sample["data"]["items"][0]
    account = Account(platform="bilibili", account_id="448167395", account_name="复旦大学")
    raw = RawPost(account=account, raw=item, post_id="BV1xx")
    post = Bilibili().parse(raw, account)
    assert post.platform == "bilibili"
    assert post.post_id == "BV1xx"
    assert post.title == "测试视频"
    assert post.caption == "简介"
    assert post.cover_url == "https://i0.hdslb.com/cover.jpg"
    assert post.duration_sec == 120
    assert post.view_count == 300
    assert post.like_count == 10
    assert post.comment_count == 2
    assert post.share_count == 1
    assert post.url == "https://www.bilibili.com/video/BV1xx"
    assert post.author_name == "复旦大学"
    assert post.author_id == "448167395"
    assert post.media_type == "video"
