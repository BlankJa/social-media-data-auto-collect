from collector.login.bilibili import login as _bilibili_login
from collector.login.douyin import login as _douyin_login
from collector.login.weibo import login as _weibo_login
from collector.registry import register_login

register_login("bilibili", _bilibili_login)
register_login("douyin", _douyin_login)
register_login("weibo", _weibo_login)
