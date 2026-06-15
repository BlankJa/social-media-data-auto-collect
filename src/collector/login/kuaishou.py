from pathlib import Path

from collector.login.common import login_with_qr


def login(out_path: Path) -> None:
    login_with_qr(
        platform="kuaishou",
        login_url="https://www.kuaishou.com/",
        required_cookies=["passToken", "kuaishou.server.web_st"],
        out_path=out_path,
    )
