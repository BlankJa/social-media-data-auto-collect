from pathlib import Path

from collector.login.common import login_with_qr


def login(out_path: Path) -> None:
    login_with_qr(
        platform="kuaishou",
        login_url="https://www.kuaishou.com/",
        # 真机实测（2026-06-16）：登录后下发 userId + kuaishou.server.webday7_st/_ph
        # （7天免登录会话），并无 plan 假设的 passToken / web_st。
        required_cookies=["userId", "kuaishou.server.webday7_st"],
        out_path=out_path,
    )
