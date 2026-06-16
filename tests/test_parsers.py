import json
from pathlib import Path

from collector.bilibili import Bilibili, _parse_count
from collector.douyin import Douyin
from collector.kuaishou import Kuaishou
from collector.weibo import Weibo
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


def test_douyin_parse():
    sample = _load("douyin/sample_response.json")
    item = sample["aweme_list"][0]
    account = Account(
        platform="douyin",
        account_id=item["author"]["sec_uid"],
        account_name=item["author"]["nickname"],
    )
    raw = RawPost(account=account, raw=item, post_id=item["aweme_id"])
    post = Douyin().parse(raw, account)
    assert post.platform == "douyin"
    assert post.post_id == item["aweme_id"]
    assert post.title == item["desc"]
    assert post.like_count == item["statistics"]["digg_count"]
    assert post.view_count == item["statistics"]["play_count"]
    assert post.collect_count == item["statistics"]["collect_count"]
    assert post.duration_sec == 65  # 65000ms -> 65s
    assert post.extras["author_bio"] == item["author"]["signature"]
    assert post.url == f"https://www.douyin.com/video/{item['aweme_id']}"


def test_weibo_parse():
    sample = _load("weibo/sample_response.json")
    item = sample["data"]["list"][0]
    account = Account(
        platform="weibo",
        account_id=str(item["user"]["id"]),
        account_name=item["user"]["screen_name"],
    )
    raw = RawPost(account=account, raw=item, post_id=item["mblogid"])
    post = Weibo().parse(raw, account)
    assert post.platform == "weibo"
    assert post.post_id == item["mblogid"]
    assert post.title == item["text_raw"]
    assert post.like_count == item["attitudes_count"]
    assert post.comment_count == item["comments_count"]
    assert post.share_count == item["reposts_count"]
    assert post.view_count == item["reads_count"]
    assert post.media_type == "image"  # 有 pic_infos 无 video
    assert "wx1.sinaimg.cn" in post.extras["image_urls"]
    assert post.author_name == "复旦大学"


def test_kuaishou_parse():
    sample = _load("kuaishou/sample_response.json")
    feed = sample["data"]["visionProfilePhotoList"]["feeds"][0]
    photo = feed["photo"]
    author = feed["author"]
    account = Account(
        platform="kuaishou", account_id=str(author["id"]), account_name=author["name"]
    )
    raw = RawPost(account=account, raw=feed, post_id=photo["id"])
    post = Kuaishou().parse(raw, account)
    assert post.platform == "kuaishou"
    assert post.post_id == photo["id"]
    assert post.title == photo["caption"]
    # 真机：likeCount/viewCount 是字符串需转 int；commentCount 为 None；无 shareCount
    assert post.view_count == int(photo["viewCount"])
    assert post.like_count == int(photo["likeCount"])
    assert post.comment_count is None
    assert post.share_count is None
    assert post.duration_sec == photo["duration"] // 1000  # 毫秒 -> 秒
    assert post.author_name == "复旦大学"
    assert post.url == f"https://www.kuaishou.com/short-video/{photo['id']}"


def test_kuaishou_parse_wan_count():
    """真机：点赞过万时 likeCount 是「121.7万」中文串，需转成整数 1217000。"""
    feed = {
        "author": {"id": "3xiz35fp79yc3cu", "name": "复旦大学"},
        "photo": {
            "id": "3xwan",
            "duration": 10000,
            "caption": "热门视频",
            "coverUrl": "https://p.example/c.jpg",
            "photoUrl": "https://v.example/v.mp4",
            "likeCount": "121.7万",
            "commentCount": None,
            "viewCount": "1.2亿",
            "timestamp": 1780704472918,
        },
    }
    account = Account(platform="kuaishou", account_id="3xiz35fp79yc3cu", account_name="复旦大学")
    raw = RawPost(account=account, raw=feed, post_id="3xwan")
    post = Kuaishou().parse(raw, account)
    assert post.like_count == 1_217_000
    assert post.view_count == 120_000_000
