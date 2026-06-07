from __future__ import annotations

from datetime import datetime, timezone, timedelta

_IST = timezone(timedelta(hours=5, minutes=30))
_FMT = "%-d %B %Y %-I:%M %p"


def parse_dt(iso: str) -> datetime:
    iso = iso.rstrip("Z")
    if iso.endswith("+00:00"):
        iso = iso[:-6]
    try:
        return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(tz=timezone.utc)


def to_ist(dt: datetime) -> str:
    return dt.astimezone(_IST).strftime(_FMT + " IST")


def now_ist() -> str:
    return datetime.now(tz=_IST).strftime(_FMT + " IST")


def now_utc_label() -> str:
    return datetime.now(tz=timezone.utc).strftime(_FMT + " UTC")
