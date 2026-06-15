from __future__ import annotations

import hashlib
import urllib.parse
from typing import Any


# 来自公开逆向：mixinKey 编码所需的索引表
_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]


def compute_mixin_key(img_key: str, sub_key: str) -> str:
    raw = img_key + sub_key
    return "".join(raw[i] for i in _MIXIN_KEY_ENC_TAB)[:32]


def sign_params(params: dict[str, Any], *, mixin_key: str, wts: int) -> dict[str, Any]:
    """按 key 字典序拼串后 md5，返回带 wts/w_rid 的新 params。"""
    p = dict(params)
    p["wts"] = wts
    # B 站需要先把 value 里的 "!'()*" 这几个保留字符过滤掉
    sanitized = {
        k: "".join(ch for ch in str(v) if ch not in "!'()*") for k, v in p.items()
    }
    query = urllib.parse.urlencode(sorted(sanitized.items()))
    p["w_rid"] = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
    return p
