from collector.signing.douyin_abogus import sign, sign_params

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_PARAMS = {"aid": "6383", "sec_user_id": "MS4wLjABAAAA-xxx", "count": "18"}


def test_sign_non_empty():
    out = sign(_PARAMS, _UA)
    assert isinstance(out, str)
    assert len(out) > 50  # a_bogus 实测约 160+ 字符


def test_sign_is_non_deterministic():
    # a_bogus 含时间/随机因子，两次调用应不同
    assert sign(_PARAMS, _UA) != sign(_PARAMS, _UA)


def test_sign_params_appends_a_bogus():
    signed = sign_params(_PARAMS, _UA)
    assert "a_bogus" in signed
    assert signed["aid"] == "6383"
    assert len(signed["a_bogus"]) > 50
