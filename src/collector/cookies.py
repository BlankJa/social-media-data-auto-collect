from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from collector.schemas import Platform


class CookieFileMissing(FileNotFoundError):
    pass


class CookieBundle(BaseModel):
    saved_at: datetime
    platform: Platform
    cookies: list[dict[str, Any]]


def save_cookies(path: Path, *, platform: Platform, cookies: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bundle = CookieBundle(
        saved_at=datetime.now(timezone.utc),
        platform=platform,
        cookies=cookies,
    )
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(path)


def load_cookies(path: Path) -> CookieBundle:
    if not path.exists():
        raise CookieFileMissing(str(path))
    return CookieBundle.model_validate_json(path.read_text(encoding="utf-8"))


def cookie_age(path: Path) -> timedelta:
    bundle = load_cookies(path)
    return datetime.now(timezone.utc) - bundle.saved_at


def to_httpx_cookies(bundle: CookieBundle) -> dict[str, str]:
    return {c["name"]: c["value"] for c in bundle.cookies}
