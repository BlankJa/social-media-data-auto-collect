from datetime import timedelta
from pathlib import Path

import pytest

from collector.cookies import (
    CookieFileMissing,
    cookie_age,
    load_cookies,
    save_cookies,
    to_httpx_cookies,
)


def test_save_then_load(tmp_path: Path):
    p = tmp_path / "bilibili.json"
    save_cookies(
        p,
        platform="bilibili",
        cookies=[{"name": "SESSDATA", "value": "x", "domain": ".bilibili.com", "path": "/"}],
    )
    data = load_cookies(p)
    assert data.platform == "bilibili"
    assert data.cookies[0]["name"] == "SESSDATA"


def test_load_missing_raises(tmp_path: Path):
    with pytest.raises(CookieFileMissing):
        load_cookies(tmp_path / "missing.json")


def test_cookie_age(tmp_path: Path):
    p = tmp_path / "bilibili.json"
    save_cookies(p, platform="bilibili", cookies=[])
    age = cookie_age(p)
    assert age < timedelta(seconds=10)


def test_to_httpx_cookies(tmp_path: Path):
    p = tmp_path / "bilibili.json"
    save_cookies(
        p,
        platform="bilibili",
        cookies=[
            {"name": "SESSDATA", "value": "abc", "domain": ".bilibili.com", "path": "/"},
            {"name": "bili_jct", "value": "def", "domain": ".bilibili.com", "path": "/"},
        ],
    )
    data = load_cookies(p)
    assert to_httpx_cookies(data) == {"SESSDATA": "abc", "bili_jct": "def"}
