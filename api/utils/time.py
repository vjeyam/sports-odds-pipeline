from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone
from typing import List, Tuple
from zoneinfo import ZoneInfo


def parse_iso_dt(s: str) -> datetime:
    """
    Parse an ISO datetime string into an *aware* datetime in UTC.
    Supports trailing 'Z' (Zulu) and '+00:00' offsets.
    """
    if not s:
        raise ValueError("empty datetime string")

    ss = s.strip()

    # Handle Zulu suffix
    if ss.endswith("Z"):
        ss = ss[:-1] + "+00:00"

    dt = datetime.fromisoformat(ss)

    # If still naive, assume UTC (SQLite sometimes stores without offset)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Normalize to UTC
    return dt.astimezone(timezone.utc)


def chicago_day_range(day: date_type) -> Tuple[datetime, datetime, ZoneInfo]:
    chi = ZoneInfo("America/Chicago")

    # Build naive local midnight then attach tz via constructor (not replace)
    start_local = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=chi)
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