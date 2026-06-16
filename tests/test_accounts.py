from pathlib import Path

from collector.accounts import (
    add_account,
    load_accounts_raw,
    parse_import_file,
    remove_account,
    validate_account_id,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_add_then_load(tmp_path: Path):
    assert add_account(tmp_path, "kuaishou", "3xabc", "复旦大学") is True
    rows = load_accounts_raw(tmp_path, "kuaishou")
    assert rows == [{"account_id": "3xabc", "account_name": "复旦大学"}]


def test_add_dedup(tmp_path: Path):
    add_account(tmp_path, "kuaishou", "3xabc", "复旦大学")
    # 同 id 再加返回 False，不重复
    assert add_account(tmp_path, "kuaishou", "3xabc", "复旦(改名)") is False
    assert len(load_accounts_raw(tmp_path, "kuaishou")) == 1


def test_written_file_has_header(tmp_path: Path):
    add_account(tmp_path, "kuaishou", "3xabc", "复旦大学")
    text = (tmp_path / "kuaishou.yaml").read_text("utf-8")
    assert text.startswith("# account_id 是快手个人主页")


def test_remove_existing(tmp_path: Path):
    add_account(tmp_path, "kuaishou", "3xabc", "复旦大学")
    add_account(tmp_path, "kuaishou", "3xdef", "另一个")
    assert remove_account(tmp_path, "kuaishou", "3xabc") is True
    rows = load_accounts_raw(tmp_path, "kuaishou")
    assert [r["account_id"] for r in rows] == ["3xdef"]


def test_remove_missing(tmp_path: Path):
    add_account(tmp_path, "kuaishou", "3xabc", "复旦大学")
    assert remove_account(tmp_path, "kuaishou", "3xzzz") is False
    assert len(load_accounts_raw(tmp_path, "kuaishou")) == 1


def test_validate_ok():
    assert validate_account_id("bilibili", "17616721") is None
    assert validate_account_id("kuaishou", "3xiz35fp79yc3cu") is None
    assert validate_account_id("douyin", "MS4wLjABAAAA") is None
    assert validate_account_id("weibo", "1729332983") is None


def test_validate_warns():
    assert validate_account_id("bilibili", "abc") is not None
    assert validate_account_id("kuaishou", "zzz") is not None
    assert validate_account_id("douyin", "123") is not None


def test_parse_import_csv():
    valid, errors = parse_import_file(FIXTURES / "import_sample.csv")
    assert [(v["platform"], v["account_id"]) for v in valid] == [
        ("kuaishou", "3xaaa"),
        ("bilibili", "123456"),
    ]
    assert len(errors) == 1  # tieba 那行
    assert errors[0][0] == 4  # 第4行（含表头第1行）


def test_parse_import_xlsx():
    valid, errors = parse_import_file(FIXTURES / "import_sample.xlsx")
    assert [v["account_id"] for v in valid] == ["MS4wLjABAAAAxyz", "3xbbb"]
    assert errors == []  # 空行被忽略，不算错误
