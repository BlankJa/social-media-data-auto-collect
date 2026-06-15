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


COLUMNS: dict[Platform, list[ColumnSpec]] = {
    "bilibili": _BILIBILI,
    # 抖音、微博、快手将在 Phase 2/3 补全
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
