from __future__ import annotations

from typing import Callable

from collector.base import Platform
from collector.bilibili import Bilibili
from collector.douyin import Douyin
from collector.weibo import Weibo


PLATFORMS: dict[str, Platform] = {
    "bilibili": Bilibili(),
    "douyin": Douyin(),
    "weibo": Weibo(),
    # 快手在 Phase 3 中注册
}


_LOGIN_FUNCS: dict[str, Callable] = {}


def register_login(name: str, fn: Callable) -> None:
    _LOGIN_FUNCS[name] = fn


def login_func(name: str) -> Callable:
    return _LOGIN_FUNCS[name]
