from __future__ import annotations

from datetime import datetime, timedelta


def _next_weekday(base: datetime) -> datetime:
    dt = base
    while dt.weekday() > 3:
        dt += timedelta(days=1)
    return dt


def suggest_send_times(now: datetime | None = None) -> tuple[str, str, str]:
    base = now or datetime.now()
    day1 = _next_weekday(base + timedelta(days=1)).replace(
        hour=8, minute=15, second=0, microsecond=0
    )
    day2 = _next_weekday(day1 + timedelta(days=3)).replace(
        hour=8, minute=45, second=0, microsecond=0
    )
    day3 = _next_weekday(day2 + timedelta(days=5)).replace(
        hour=16, minute=15, second=0, microsecond=0
    )
    fmt = "%Y-%m-%d %H:%M"
    return day1.strftime(fmt), day2.strftime(fmt), day3.strftime(fmt)
