from pathlib import Path

from collector.login.common import login_with_qr


def login(out_path: Path) -> None:
    # 微博一进页面就给访客设 SUB/SUBP，且微信/扫码登录不一定写 SSOLoginState，
    # 因此不靠 cookie 名判断，改用"登录成功后页面跳离登录页"作为完成信号。
    login_with_qr(
        platform="weibo",
        login_url="https://weibo.com/login.php",
        login_url_markers=["login", "passport", "signin"],
        out_path=out_path,
    )
