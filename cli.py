from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import typer
import yaml
from loguru import logger
from openpyxl import Workbook

from collector import login as _login_mod  # noqa: F401  触发登录注册
from collector.accounts import (
    PLATFORMS as ACCOUNT_PLATFORMS,
    add_account,
    load_accounts_raw,
    parse_import_file,
    remove_account,
    validate_account_id,
)
from collector.base import Platform as PlatformProtocol, collect_account
from collector.cookies import load_cookies, to_httpx_cookies
from collector.registry import PLATFORMS, login_func
from collector.rendering import render_xlsx, report_filename
from collector.schemas import Account, Platform, Post
from collector.status import (
    CookieHealth,
    FailedAccount,
    PlatformStatus,
    RunStatus,
    count_recent_posts,
    read_status,
    render_status_panel,
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


account_app = typer.Typer(help="账号清单管理（免编 YAML）")
app.add_typer(account_app, name="account")


def _pick_platform() -> str:
    typer.echo("选平台：")
    for i, p in enumerate(ACCOUNT_PLATFORMS, start=1):
        typer.echo(f"  [{i}] {p}")
    idx = typer.prompt("输入序号", type=int)
    if not 1 <= idx <= len(ACCOUNT_PLATFORMS):
        raise typer.BadParameter("序号超出范围")
    return ACCOUNT_PLATFORMS[idx - 1]


@account_app.command("list")
def account_list():
    """列出四平台所有账号。"""
    from rich.console import Console
    from rich.table import Table

    table = Table(title="账号清单")
    table.add_column("平台")
    table.add_column("account_id")
    table.add_column("名称")
    for name in ACCOUNT_PLATFORMS:
        for a in load_accounts_raw(CONFIG_ROOT, name):
            table.add_row(name, a["account_id"], a["account_name"])
    Console().print(table)


@account_app.command("add")
def account_add(
    platform: str = typer.Argument(None),
    account_id: str = typer.Argument(None),
    name: str = typer.Argument(None),
):
    """加一个账号。省略参数则交互式提问。"""
    if platform is None:
        platform = _pick_platform()
    elif platform not in ACCOUNT_PLATFORMS:
        raise typer.BadParameter(f"平台须是 {ACCOUNT_PLATFORMS} 之一")
    if account_id is None:
        account_id = typer.prompt("account_id")
    if name is None:
        name = typer.prompt("账号名称", default=account_id)

    warn = validate_account_id(platform, account_id)
    if warn:
        typer.secho(f"⚠️ {warn}", fg=typer.colors.YELLOW)
    if add_account(CONFIG_ROOT, platform, account_id, name):
        typer.secho(f"✅ 已加入 configs/{platform}.yaml", fg=typer.colors.GREEN)
    else:
        typer.secho(f"已存在，未重复添加：{account_id}", fg=typer.colors.YELLOW)


@account_app.command("remove")
def account_remove(
    platform: str = typer.Argument(None),
    account_id: str = typer.Argument(None),
):
    """删一个账号。省略参数则交互式选择。"""
    if platform is None:
        platform = _pick_platform()
    elif platform not in ACCOUNT_PLATFORMS:
        raise typer.BadParameter(f"平台须是 {ACCOUNT_PLATFORMS} 之一")
    if account_id is None:
        rows = load_accounts_raw(CONFIG_ROOT, platform)
        if not rows:
            typer.echo("该平台暂无账号")
            raise typer.Exit()
        for i, a in enumerate(rows, start=1):
            typer.echo(f"  [{i}] {a['account_id']}  {a['account_name']}")
        idx = typer.prompt("删哪个（序号）", type=int)
        if not 1 <= idx <= len(rows):
            raise typer.BadParameter("序号超出范围")
        account_id = rows[idx - 1]["account_id"]

    if remove_account(CONFIG_ROOT, platform, account_id):
        typer.secho(f"✅ 已从 configs/{platform}.yaml 删除 {account_id}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"未找到：{account_id}", fg=typer.colors.YELLOW)


@account_app.command("import")
def account_import(file: str):
    """从 .xlsx / .csv 批量导入账号（三列：platform / account_id / account_name）。"""
    valid, errors = parse_import_file(Path(file))
    added = skipped = 0
    for v in valid:
        if add_account(CONFIG_ROOT, v["platform"], v["account_id"], v["account_name"]):
            added += 1
        else:
            skipped += 1
    msg = f"新增 {added} 个 · 跳过 {skipped} 个(已存在) · 无效 {len(errors)} 个"
    typer.secho(msg, fg=typer.colors.GREEN)
    for row_no, reason in errors:
        typer.secho(f"  无效 row{row_no}: {reason}", fg=typer.colors.YELLOW)


@account_app.command("template")
def account_template(out: str = typer.Argument("account_template.xlsx")):
    """生成带表头的空导入模板 xlsx。"""
    wb = Workbook()
    ws = wb.active
    ws.append(["platform", "account_id", "account_name"])
    wb.save(out)
    typer.secho(
        f"✅ 模板已写 {out}（platform 填 bilibili/weibo/douyin/kuaishou）",
        fg=typer.colors.GREEN,
    )


@app.command()
def login(platform: str):
    """弹浏览器扫码，cookie 落 cookies/<platform>.json"""
    fn = login_func(platform)
    out = COOKIE_ROOT / f"{platform}.json"
    fn(out)


def _run_accounts(
    name: str,
    plat: PlatformProtocol,
    accounts: list[Account],
    cookies: dict[str, str],
    data_root: Path,
    *,
    full: bool,
) -> PlatformStatus:
    """串行采集单个平台的所有账号，聚合成 PlatformStatus（节流在 collect_account 内）。

    collect_account 已 per-account 捕获异常并把 error 写进 CollectResult，
    所以单账号失败只记一条 failed_account、不阻塞其余账号。
    """
    ok = failed = new_total = 0
    health: CookieHealth = "ok"
    failures: list[FailedAccount] = []
    for account in accounts:
        logger.info(
            "collect_start platform={} account={} mode={}",
            name, account.account_id, "full" if full else "incremental",
        )
        result = collect_account(plat, account, cookies, data_root, full=full)
        logger.info(
            "collect_done new_posts={} stopped_at={} error={}",
            result.new_posts, result.stopped_at, result.error,
        )
        new_total += result.new_posts
        if result.error:
            failed += 1
            failures.append(FailedAccount(
                account_id=account.account_id,
                account_name=account.account_name,
                error=result.error[:200],
            ))
        else:
            ok += 1
        if result.cookie_health == "expired":
            health = "expired"
        elif result.cookie_health == "warning" and health == "ok":
            health = "warning"
    return PlatformStatus(
        accounts_total=len(accounts), accounts_ok=ok, accounts_failed=failed,
        new_posts=new_total, new_posts_7d=count_recent_posts(data_root, name),
        cookie_health=health,
        failed_accounts=failures,
    )


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
    """显示采集健康面板：cookie 年龄 + 近7天 + 建议。"""
    rs = read_status(STATUS_PATH) if STATUS_PATH.exists() else None
    render_status_panel(list(PLATFORMS.keys()), COOKIE_ROOT, DATA_ROOT, rs)


def select_render_posts(
    platform: str, data_root: Path, accounts: list[Account]
) -> list[Post]:
    """渲染选取：账号目录下全部 JSON（当前主页全量快照），只认 config 登记的账号。

    不按日期过滤——data/ 是当前主页快照（ADR-0003），增量后旧帖不再重采，
    所以「只渲当天采到的」会漏掉历史。盘上残留但已从 config 移除的账号目录也不取。
    """
    posts: list[Post] = []
    plat_dir = data_root / platform
    if not plat_dir.exists():
        return posts
    for account in accounts:
        acc_dir = plat_dir / account.account_id
        if not acc_dir.is_dir():
            continue
        for f in acc_dir.glob("*.json"):
            if f.name == "_meta.json":
                continue
            posts.append(Post.model_validate(json.loads(f.read_text("utf-8"))))
    return posts


@app.command()
def render(
    platform: str,
    date: str = typer.Option(None, "--date"),
    full: bool = typer.Option(False, "--full"),
):
    """从 data/ 渲染当前主页全量快照的 Excel。文件名按渲染日命名（默认今天）。"""
    names = list(PLATFORMS.keys()) if platform == "all" else [platform]
    when = datetime.fromisoformat(date) if date else datetime.now()
    for name in names:
        posts = select_render_posts(name, DATA_ROOT, _load_accounts(name))
        out = REPORT_ROOT / report_filename(name, when, full=full)
        render_xlsx(out, platform=name, posts=posts)
        logger.info("rendered {} ({} rows) -> {}", name, len(posts), out)


if __name__ == "__main__":
    app()
