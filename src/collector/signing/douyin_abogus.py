from __future__ import annotations

import urllib.parse
from typing import Any

from f2.apps.douyin.utils import ABogusManager


def sign(params: dict[str, Any], user_agent: str) -> str:
    """对抖音 web 接口参数生成 a_bogus 签名值。

    抖音 2024-06 起弃用 X-Bogus，改用 a_bogus。该算法含时间/随机因子，
    输出非确定（同输入每次不同），因此不固化已知向量。
    底层复用 f2(Johnserf-Seed/f2) 的 ABogusManager，避免自行维护易碎算法。
    """
    query = urllib.parse.urlencode(params)
    endpoint = ABogusManager.str_2_endpoint(user_agent, query)
    return endpoint.split("a_bogus=", 1)[1]


def sign_params(params: dict[str, Any], user_agent: str) -> dict[str, Any]:
    """返回带 a_bogus 的新 params（与 bilibili sign_params 风格一致）。"""
    p = dict(params)
    p["a_bogus"] = sign(params, user_agent)
    return p
