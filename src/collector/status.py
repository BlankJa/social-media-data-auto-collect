from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from collector.cookies import CookieFileMissing, cookie_age
from collector.schemas import Platform

CookieHealth = Literal["ok", "warning", "expired"]

# cookie 年龄预警阈值（天）。快手是 7 天会话，提前 1 天预警。
COOKIE_AGE_WARN_DAYS = {"kuaishou": 6, "bilibili": 25, "weibo": 25, "douyin": 25}


def cookie_advice(
    platform: str, cookie_path: Path, last_run_health: str | None
) -> tuple[str, str]:
    """返回 (年龄文本, 建议)。优先级：缺文件 > 上次运行已过期 > 年龄超阈值 > 正常。"""
    if not cookie_path.exists():
        return "—", "❌ 未登录，需扫码"
    try:
        days = cookie_age(cookie_path).days
    except CookieFileMissing:
        return "—", "❌ 未登录，需扫码"
    age_text = f"{days}天"
    if last_run_health == "expired":
        return age_text, "❌ 已过期，需重扫"
    if days > COOKIE_AGE_WARN_DAYS.get(platform, 25):
        return age_text, "⚠️ 快过期，建议重扫"
    return age_text, "✅ 正常"


class FailedAccount(BaseModel):
    account_id: str
    account_name: str
    error: str


class PlatformStatus(BaseModel):
    accounts_total: int
    accounts_ok: int
    accounts_failed: int
    new_posts: int
    new_posts_7d: int
    cookie_health: CookieHealth
    failed_accounts: list[FailedAccount] = []


class RunStatus(BaseModel):
    last_run_started_at: datetime
    last_run_finished_at: datetime
    last_run_mode: Literal["incremental", "full"]
    platforms: dict[str, PlatformStatus]


def write_status(path: Path, status: RunStatus) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(status.model_dump_json(indent=2), encoding="utf-8")


def read_status(path: Path) -> RunStatus:
    return RunStatus.model_validate_json(path.read_text("utf-8"))


def count_recent_posts(data_root: Path, platform: Platform, *, days: int = 7) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    plat = data_root / platform
    if not plat.exists():
        return 0
    n = 0
    for acc in plat.iterdir():
        if not acc.is_dir():
            continue
        for f in acc.glob("*.json"):
            if f.name == "_meta.json":
                continue
            try:
                raw = json.loads(f.read_text("utf-8"))["fetched_at"]
                # py3.11 fromisoformat 不吃 'Z' 后缀
                fetched = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if fetched.tzinfo is None:
                    fetched = fetched.replace(tzinfo=timezone.utc)
                if fetched >= cutoff:
                    n += 1
            except Exception:
                continue
    return n


def render_status_panel(
    platforms: list[str],
    cookie_root: Path,
    data_root: Path,
    run_status: "RunStatus | None",
) -> None:
    """实时面板：cookie 年龄 + 近7天 + 账号 ok/total + 建议；表下列出失败账号。"""
    console = Console()
    table = Table(title="新媒体采集状态")
    table.add_column("平台")
    table.add_column("Cookie 年龄")
    table.add_column("近7天")
    table.add_column("账号")
    table.add_column("建议")
    failures: list[tuple[str, str, str, str]] = []  # (平台, 名称, id, error)
    for name in platforms:
        health = None
        accounts_text = "—"
        if run_status is not None and name in run_status.platforms:
            ps = run_status.platforms[name]
            health = ps.cookie_health
            accounts_text = f"{ps.accounts_ok}/{ps.accounts_total} ✓"
            for fa in ps.failed_accounts:
                failures.append((name, fa.account_name, fa.account_id, fa.error))
        age_text, advice = cookie_advice(name, cookie_root / f"{name}.json", health)
        n7 = count_recent_posts(data_root, name)
        table.add_row(name, age_text, str(n7), accounts_text, advice)
    console.print(table)
    if failures:
        console.print("[red]❌ 失败账号：[/red]")
        for plat, acc_name, acc_id, err in failures:
            console.print(f"  {plat} / {acc_name} ({acc_id})：{err}")
    console.print("重扫命令：cli.py login <平台>")
