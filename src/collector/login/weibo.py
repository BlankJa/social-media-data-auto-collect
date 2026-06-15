from pathlib import Path

from collector.login.common import login_with_qr


def login(out_path: Path) -> None:
    login_with_qr(
        platform="weibo",
        login_url="https://weibo.com/login.php",
        required_cookies=["SUB", "SUBP"],
        out_path=out_path,
    )
