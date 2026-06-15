from pathlib import Path

from collector.login.common import login_with_qr


def login(out_path: Path) -> None:
    login_with_qr(
        platform="bilibili",
        login_url="https://passport.bilibili.com/login",
        required_cookies=["SESSDATA", "bili_jct", "DedeUserID"],
        out_path=out_path,
    )
