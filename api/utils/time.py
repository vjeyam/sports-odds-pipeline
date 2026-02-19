from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone
from typing import List, Tuple
from zoneinfo import ZoneInfo


def parse_iso_dt(s: str) -> datetime:
    # Handles "Z" and "+00:00"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def chicago_day_range(day: date_type) -> Tuple[datetime, datetime, ZoneInfo]:
    chi = ZoneInfo("America/Chicago")
    start_local = datetime.combine(day, time.min).replace(tzinfo=chi)
    end_local = start_local + timedelta(days=1)
    return start_local, end_local, chi


def date_range_inclusive(start: date_type, end: date_type) -> List[date_type]:
    if end < start:
        return []
    out: List[date_type] = []
    d = start
    while d <= end:
        out.append(d)
        d = d + timedelta(days=1)
    return out


def profit_for_win_american(odds_american: int) -> float:
    # $1 stake profit only (excluding returned stake)
    if odds_american < 0:
        return 100.0 / abs(float(odds_american))
    return float(odds_american) / 100.0