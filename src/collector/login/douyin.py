from pathlib import Path

from collector.login.common import login_with_qr


def login(out_path: Path) -> None:
    login_with_qr(
        platform="douyin",
        login_url="https://www.douyin.com/",
        required_cookies=["sessionid", "sessionid_ss"],
        out_path=out_path,
    )
