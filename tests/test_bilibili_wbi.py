from collector.signing.bilibili_wbi import compute_mixin_key, sign_params


def test_compute_mixin_key():
    # 已知样例：来自 SocialSisterYi/bilibili-API-collect wbi.md
    img_key = "7cd084941338484aae1ad9425b84077c"
    sub_key = "4932caff0ff746eab6f01bf08b70ac45"
    mixin = compute_mixin_key(img_key, sub_key)
    assert mixin == "ea1db124af3c7062474693fa704f4ff8"


def test_sign_params_deterministic():
    mixin = "ea1db124af3c7062474693fa704f4ff8"
    params = {"foo": "114", "bar": "514", "baz": "1919810"}
    signed = sign_params(params, mixin_key=mixin, wts=1702204169)
    assert signed["wts"] == 1702204169
    # 固化值：用本函数对上述输入跑一次得到
    assert signed["w_rid"] == "6149fdadf571698ca7e6a567265cd0ee"
