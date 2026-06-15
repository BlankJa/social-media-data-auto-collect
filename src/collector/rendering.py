from __future__ import annotations

from datetime import datetime
from pathlib import Path

import openpyxl

from collector.schemas import ColumnSpec, Platform, Post


def _fmt_dt(dt: datetime | None) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _fmt_dur_hms(sec: int | None) -> str | None:
    if sec is None:
        return None
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fmt_dur_mmss(sec: int | None) -> str | None:
    if sec is None:
        return None
    m, s = divmod(sec, 60)
    return f"{m:02d}:{s:02d}"


_BILIBILI: list[ColumnSpec] = [
    ColumnSpec(name="发布者", extract=lambda p: p.author_name),
    ColumnSpec(name="页面源码1", extract=lambda p: None),
    ColumnSpec(name="标题", extract=lambda p: p.title),
    ColumnSpec(name="视频链接", extract=lambda p: p.url),
    ColumnSpec(name="播放数", extract=lambda p: p.view_count),
    ColumnSpec(name="发布时间", extract=lambda p: _fmt_dt(p.published_at)),
    ColumnSpec(name="时长", extract=lambda p: _fmt_dur_hms(p.duration_sec)),
    ColumnSpec(name="视频封面链接", extract=lambda p: p.cover_url),
    ColumnSpec(name="视频封面链接_保存位置", extract=lambda p: None),
]


_DOUYIN: list[ColumnSpec] = [
    ColumnSpec(name="博主名称", extract=lambda p: p.author_name),
    ColumnSpec(name="博主简介", extract=lambda p: p.extras.get("author_bio", "")),
    ColumnSpec(name="视频标题", extract=lambda p: p.title),
    ColumnSpec(name="视频链接", extract=lambda p: p.url),
    ColumnSpec(name="视频点赞数", extract=lambda p: p.like_count),
    ColumnSpec(name="封面图url", extract=lambda p: p.cover_url),
    ColumnSpec(name="是否置顶", extract=lambda p: "否"),
    ColumnSpec(name="发布时间", extract=lambda p: _fmt_dt(p.published_at)),
    ColumnSpec(name="视频时长", extract=lambda p: _fmt_dur_mmss(p.duration_sec)),
    ColumnSpec(name="评论数", extract=lambda p: p.comment_count),
    ColumnSpec(name="收藏数", extract=lambda p: p.collect_count),
    ColumnSpec(name="转发数", extract=lambda p: p.share_count),
    ColumnSpec(name="页面网址", extract=lambda p: p.url),
]


_WEIBO: list[ColumnSpec] = [
    ColumnSpec(name="博主昵称", extract=lambda p: p.author_name),
    ColumnSpec(name="页面网址", extract=lambda p: f"https://weibo.com/u/{p.author_id}"),
    ColumnSpec(name="发布时间", extract=lambda p: _fmt_dt(p.published_at)),
    ColumnSpec(name="详情链接", extract=lambda p: p.url),
    ColumnSpec(name="博文内容", extract=lambda p: p.title),
    ColumnSpec(name="视频链接", extract=lambda p: p.extras.get("video_url", "")),
    ColumnSpec(name="图片链接", extract=lambda p: p.extras.get("image_urls", "")),
    ColumnSpec(name="转发数", extract=lambda p: p.share_count),
    ColumnSpec(name="评论数", extract=lambda p: p.comment_count),
    ColumnSpec(name="点赞数", extract=lambda p: p.like_count),
]


_KUAISHOU: list[ColumnSpec] = [
    ColumnSpec(name="快手个人账号链接", extract=lambda p: f"https://www.kuaishou.com/profile/{p.author_id}"),
    ColumnSpec(name="视频封面图地址", extract=lambda p: p.cover_url),
    ColumnSpec(name="视频点赞数", extract=lambda p: p.like_count),
    ColumnSpec(name="快手个人账号名称", extract=lambda p: p.author_name),
    ColumnSpec(name="视频地址", extract=lambda p: p.url),
    ColumnSpec(name="视频标题", extract=lambda p: p.title),
    ColumnSpec(name="视频发布时间", extract=lambda p: _fmt_dt(p.published_at)),
    ColumnSpec(name="视频详情链接", extract=lambda p: p.url),
]


COLUMNS: dict[Platform, list[ColumnSpec]] = {
    "bilibili": _BILIBILI,
    "douyin": _DOUYIN,
    "weibo": _WEIBO,
    "kuaishou": _KUAISHOU,
}


REPORT_BASE_NAMES: dict[Platform, str] = {
    "bilibili": "B站UP主主页视频采集",
    "weibo": "微博-博主主页的博文",
    "douyin": "抖音-博主主页视频采集（不含置顶视频）",
    "kuaishou": "快手-个人账号视频采集（包含置定视频）",
}


def report_filename(platform: Platform, date: datetime, *, full: bool = False) -> str:
    base = REPORT_BASE_NAMES[platform]
    suffix = "-全量" if full else ""
    return f"{base}-{date:%Y.%m.%d}{suffix}.xlsx"


def render_xlsx(out_path: Path, *, platform: Platform, posts: list[Post]) -> None:
    cols = COLUMNS[platform]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append([c.name for c in cols])
    for p in posts:
        ws.append([c.extract(p) for c in cols])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
