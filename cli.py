from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import typer
import yaml
from loguru import logger

from collector import login as _login_mod  # noqa: F401  触发登录注册
from collector.base import collect_account
from collector.cookies import load_cookies, to_httpx_cookies
from collector.registry import PLATFORMS, login_func
from collector.rendering import render_xlsx, report_filename
from collector.schemas import Account, Platform, Post
from collector.status import (
    PlatformStatus,
    RunStatus,
    count_recent_posts,
    read_status,
    render_status_table,
    write_status,
)


app = typer.Typer(add_completion=False)

REPO = Path(__file__).parent.resolve()
DATA_ROOT = REPO / "data"
COOKIE_ROOT = REPO / "cookies"
CONFIG_ROOT = REPO / "configs"
REPORT_ROOT = REPO / "reports"
STATUS_PATH = REPO / "status.json"


def _load_accounts(platform: Platform) -> list[Account]:
    raw = yaml.safe_load((CONFIG_ROOT / f"{platform}.yaml").read_text("utf-8"))
    return [Account(platform=platform, **r) for r in raw]


@app.command()
def login(platform: str):
    """弹浏览器扫码，cookie 落 cookies/<platform>.json"""
    fn = login_func(platform)
    out = COOKIE_ROOT / f"{platform}.json"
    fn(out)


@app.command()
def collect(platform: str, full: bool = typer.Option(False, "--full")):
    """对单个平台或 all 跑增量 / 全量。"""
    names = list(PLATFORMS.keys()) if platform == "all" else [platform]
    started = datetime.now()
    plat_statuses: dict[str, PlatformStatus] = {}
    for name in names:
        plat = PLATFORMS[name]
        try:
            cookies = to_httpx_cookies(load_cookies(COOKIE_ROOT / f"{name}.json"))
        except Exception:
            logger.warning("{} 无 cookie，跳过（标记 expired）", name)
            plat_statuses[name] = PlatformStatus(
                accounts_total=0, accounts_ok=0, accounts_failed=0,
                new_posts=0, new_posts_7d=count_recent_posts(DATA_ROOT, name),
                cookie_health="expired",
            )
            continue

        accounts = _load_accounts(name)
        ok = failed = new_total = 0
        health: str = "ok"
        for account in accounts:
            logger.info(
                "collect_start platform={} account={} mode={}",
                name,
                account.account_id,
                "full" if full else "incremental",
            )
            result = collect_account(plat, account, cookies, DATA_ROOT, full=full)
            logger.info(
                "collect_done new_posts={} stopped_at={} error={}",
                result.new_posts,
                result.stopped_at,
                result.error,
            )
            new_total += result.new_posts
            if result.error:
                failed += 1
            else:
                ok += 1
            if result.cookie_health == "expired":
                health = "expired"
            elif result.cookie_health == "warning" and health == "ok":
                health = "warning"
        plat_statuses[name] = PlatformStatus(
            accounts_total=len(accounts), accounts_ok=ok, accounts_failed=failed,
            new_posts=new_total, new_posts_7d=count_recent_posts(DATA_ROOT, name),
            cookie_health=health,  # type: ignore[arg-type]
        )

    # 合并：单平台跑只更新该平台行，保留其余平台上次的状态
    merged = dict(plat_statuses)
    if STATUS_PATH.exists():
        try:
            for k, v in read_status(STATUS_PATH).platforms.items():
                merged.setdefault(k, v)
        except Exception:
            pass
    write_status(STATUS_PATH, RunStatus(
        last_run_started_at=started,
        last_run_finished_at=datetime.now(),
        last_run_mode="full" if full else "incremental",
        platforms=merged,
    ))


@app.command()
def status():
    """显示最近一次跑的健康面板。"""
    render_status_table(read_status(STATUS_PATH))


@app.command()
def render(
    platform: str,
    date: str = typer.Option(None, "--date"),
    full: bool = typer.Option(False, "--full"),
):
    """从 data/ 渲染指定日期的 Excel。默认今天。"""
    names = list(PLATFORMS.keys()) if platform == "all" else [platform]
    when = datetime.fromisoformat(date) if date else datetime.now()
    for name in names:
        posts: list[Post] = []
        plat_dir = DATA_ROOT / name
        if not plat_dir.exists():
            continue
        for acc_dir in plat_dir.iterdir():
            if not acc_dir.is_dir():
                continue
            for f in acc_dir.glob("*.json"):
                if f.name == "_meta.json":
                    continue
                data = json.loads(f.read_text("utf-8"))
                if data["fetched_at"].startswith(when.strftime("%Y-%m-%d")):
                    posts.append(Post.model_validate(data))
        out = REPORT_ROOT / report_filename(name, when, full=full)
        render_xlsx(out, platform=name, posts=posts)
        logger.info("rendered {} ({} rows) -> {}", name, len(posts), out)


if __name__ == "__main__":
    app()
