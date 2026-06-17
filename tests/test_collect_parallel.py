from datetime import datetime, timezone
from pathlib import Path

from collector.schemas import Account, Post, RawPost


def _fake_post(account: Account, raw: RawPost) -> Post:
    return Post(
        platform="bilibili", post_id=raw.post_id,
        url=f"https://b/{raw.post_id}", title=raw.post_id, media_type="video",
        published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        author_id=account.account_id, author_name=account.account_name,
        fetched_at=datetime(2026, 6, 8, tzinfo=timezone.utc), raw={},
    )


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
        return _fake_post(account, raw)

    def cookie_health(self, last_response):
        return "ok"


class HealthPlatform:
    """每个账号返回 health_by_account 指定的 cookie_health。"""

    name = "bilibili"

    def __init__(self, health_by_account: dict[str, str]):
        self.health_by_account = health_by_account
        self._current = "ok"
        self.last_response = {}

    def fetch_user_feed(self, account, cookies, since_post_id):
        self._current = self.health_by_account.get(account.account_id, "ok")
        yield RawPost(
            account=account, raw={"id": account.account_id},
            post_id=f"P_{account.account_id}",
        )

    def parse(self, raw, account):
        return _fake_post(account, raw)

    def cookie_health(self, last_response):
        return self._current


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


def test_run_accounts_expired_dominates(tmp_path):
    from cli import _run_accounts
    plat = HealthPlatform({"A1": "warning", "A2": "expired", "A3": "ok"})
    st = _run_accounts(
        "bilibili", plat, _accounts("A1", "A2", "A3"),
        cookies={}, data_root=tmp_path, full=True,
    )
    assert st.cookie_health == "expired"


def test_run_accounts_warning_when_no_expired(tmp_path):
    from cli import _run_accounts
    plat = HealthPlatform({"A1": "ok", "A2": "warning", "A3": "ok"})
    st = _run_accounts(
        "bilibili", plat, _accounts("A1", "A2", "A3"),
        cookies={}, data_root=tmp_path, full=True,
    )
    assert st.cookie_health == "warning"


def test_collect_platform_missing_cookie_returns_expired(tmp_path):
    """cookie 文件不存在 → 返回 expired 兜底，零账号。"""
    from cli import collect_platform
    st = collect_platform("bilibili", tmp_path / "cookies", tmp_path / "data", full=False)
    assert st.cookie_health == "expired"
    assert st.accounts_total == 0
    assert st.accounts_ok == 0
    assert st.accounts_failed == 0


def test_collect_platform_unexpected_error_returns_warning(tmp_path, monkeypatch):
    """cookie 正常但 _load_accounts 抛异常 → warning 兜底 + 一条 FailedAccount。"""
    import cli
    monkeypatch.setattr(cli, "load_cookies", lambda p: {})
    monkeypatch.setattr(cli, "to_httpx_cookies", lambda c: {})

    def boom(name):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(cli, "_load_accounts", boom)
    st = cli.collect_platform("bilibili", tmp_path / "cookies", tmp_path / "data", full=False)
    assert st.cookie_health == "warning"
    assert st.accounts_total == 0
    assert st.failed_accounts
    assert st.failed_accounts[0].account_id == "-"
    assert "kaboom" in st.failed_accounts[0].error


def test_collect_all_runs_every_platform(tmp_path, monkeypatch):
    """collect('all') 经线程池跑完四平台，status.json 含全部四行。"""
    import cli
    from collector.status import PlatformStatus, read_status

    seen = []

    def fake_collect_platform(name, cookie_root, data_root, *, full):
        seen.append(name)
        return PlatformStatus(
            accounts_total=1, accounts_ok=1, accounts_failed=0,
            new_posts=0, new_posts_7d=0, cookie_health="ok",
        )

    monkeypatch.setattr(cli, "collect_platform", fake_collect_platform)
    monkeypatch.setattr(cli, "STATUS_PATH", tmp_path / "status.json")

    cli.collect("all", full=False)

    assert set(seen) == set(cli.PLATFORMS.keys())
    rs = read_status(tmp_path / "status.json")
    assert set(rs.platforms.keys()) == set(cli.PLATFORMS.keys())
