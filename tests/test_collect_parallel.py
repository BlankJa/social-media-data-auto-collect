from datetime import datetime, timezone
from pathlib import Path

from collector.schemas import Account, Post, RawPost


class FlakyPlatform:
    """指定 bad_id 的账号 fetch 时抛异常，其余正常返回 1 条。"""

    name = "bilibili"

    def __init__(self, bad_id: str):
        self.bad_id = bad_id
        self.last_response = {}

    def fetch_user_feed(self, account, cookies, since_post_id):
        if account.account_id == self.bad_id:
            raise RuntimeError("boom")
        yield RawPost(
            account=account, raw={"id": account.account_id},
            post_id=f"P_{account.account_id}",
        )

    def parse(self, raw, account):
        return Post(
            platform="bilibili", post_id=raw.post_id,
            url=f"https://b/{raw.post_id}", title=raw.post_id, media_type="video",
            published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            author_id=account.account_id, author_name=account.account_name,
            fetched_at=datetime(2026, 6, 8, tzinfo=timezone.utc), raw={},
        )

    def cookie_health(self, last_response):
        return "ok"


def _accounts(*ids: str) -> list[Account]:
    return [Account(platform="bilibili", account_id=i, account_name=i) for i in ids]


def test_run_accounts_isolates_failure(tmp_path: Path):
    from cli import _run_accounts
    plat = FlakyPlatform(bad_id="A2")
    st = _run_accounts(
        "bilibili", plat, _accounts("A1", "A2", "A3"),
        cookies={}, data_root=tmp_path, full=True,
    )
    assert st.accounts_total == 3
    assert st.accounts_ok == 2
    assert st.accounts_failed == 1
    assert [f.account_id for f in st.failed_accounts] == ["A2"]
    assert "boom" in st.failed_accounts[0].error
    assert (tmp_path / "bilibili" / "A1" / "P_A1.json").exists()
    assert (tmp_path / "bilibili" / "A3" / "P_A3.json").exists()
