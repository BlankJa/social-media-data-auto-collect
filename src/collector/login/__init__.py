from collector.login.bilibili import login as _bilibili_login
from collector.registry import register_login

register_login("bilibili", _bilibili_login)
