from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from collector.cookies import save_cookies
from collector.schemas import Platform


@contextmanager
def fresh_chromium(headless: bool = False) -> Iterator[webdriver.Chrome]:
    """纯净 chromium，不复用本机 profile。退出自动关闭。"""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    driver = webdriver.Chrome(options=opts)
    try:
        yield driver
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def wait_for_cookies(
    driver: webdriver.Chrome, required: list[str], *, timeout: int = 600
) -> list[dict]:
    """轮询直到 required 中所有 cookie 名都出现，或超时。"""
    deadline = time.time() + timeout
    missing: list[str] = list(required)
    while time.time() < deadline:
        cookies = driver.get_cookies()
        names = {c["name"] for c in cookies}
        missing = [n for n in required if n not in names]
        if not missing:
            return cookies
        logger.debug("waiting for cookies: missing={}", missing)
        time.sleep(2)
    raise TimeoutError(f"cookie wait timed out; still missing: {missing}")


def wait_for_login_redirect(
    driver: webdriver.Chrome, login_url_markers: list[str], *, timeout: int = 600
) -> list[dict]:
    """轮询直到当前 URL 不再包含任何登录页特征串（即跳离登录页 = 登录成功），或超时。

    比"等某个具体 cookie 名"更稳——不依赖各平台 cookie 命名细节。
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        url = driver.current_url
        if url and not any(m in url for m in login_url_markers):
            time.sleep(2)  # 给跳转后 cookie 落定一点时间
            return driver.get_cookies()
        logger.debug("waiting for login redirect, current_url={}", url)
        time.sleep(2)
    raise TimeoutError(f"login redirect timed out; still on {driver.current_url}")


def login_with_qr(
    *,
    platform: Platform,
    login_url: str,
    out_path: Path,
    required_cookies: list[str] | None = None,
    login_url_markers: list[str] | None = None,
) -> None:
    """扫码登录并落盘 cookie。

    两种登录完成判据二选一：
    - required_cookies：等这些 cookie 名都出现（适合有明确登录态 cookie 的平台）
    - login_url_markers：等 URL 跳离登录页（适合 cookie 命名不可靠的平台，如微博）
    """
    print(
        f"请在弹出的浏览器里扫码登录 {platform}，扫完不要关浏览器，等终端提示完成…"
    )
    with fresh_chromium() as driver:
        driver.get(login_url)
        if login_url_markers is not None:
            cookies = wait_for_login_redirect(driver, login_url_markers)
        else:
            assert required_cookies is not None, "需提供 required_cookies 或 login_url_markers"
            cookies = wait_for_cookies(driver, required_cookies)
    save_cookies(out_path, platform=platform, cookies=cookies)
    print(f"✅ {platform} 登录态已写入 {out_path}")
