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


def login_with_qr(
    *,
    platform: Platform,
    login_url: str,
    required_cookies: list[str],
    out_path: Path,
) -> None:
    print(
        f"请在弹出的浏览器里扫码登录 {platform}，扫完不要关浏览器，等终端提示完成…"
    )
    with fresh_chromium() as driver:
        driver.get(login_url)
        cookies = wait_for_cookies(driver, required_cookies)
    save_cookies(out_path, platform=platform, cookies=cookies)
    print(f"✅ {platform} 登录态已写入 {out_path}")
