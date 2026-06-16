from pathlib import Path

from collector.accounts import add_account, load_accounts_raw


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
