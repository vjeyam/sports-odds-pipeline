from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Sequence

from src.extract.espn_api import fetch_nba_scoreboard
from src.load.raw_results_loader import flatten_espn_scoreboard, upsert_raw_espn_results


TZ = ZoneInfo("America/Chicago")


def default_dates() -> list[str]:
    today_local = datetime.now(TZ).date()
    yday_local = today_local - timedelta(days=1)
    return [yday_local.strftime("%Y%m%d"), today_local.strftime("%Y%m%d")]


def run_espn_results_pull(
    *,
    db_path: str = "odds.sqlite",
    dates: Optional[Sequence[str]] = None,
    league: str = "nba",
) -> dict:
    """
    Programmatic entrypoint (used by Streamlit).
    Pulls ESPN scoreboard for given YYYYMMDD dates (defaults to yesterday+today).
    Returns a summary dict.
    """
    ds = list(dates) if dates else default_dates()

    total_rows = 0
    per_date = []
    for d in ds:
        payload = fetch_nba_scoreboard(d)
        rows = flatten_espn_scoreboard(d, payload, league=league)
        upsert_raw_espn_results(db_path, rows)
        per_date.append({"date": d, "espn_events": len(rows)})
        total_rows += len(rows)

    return {"dates": ds, "league": league, "per_date": per_date, "total_rows_upserted": total_rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="odds.sqlite")
    ap.add_argument("--date", action="append", help="YYYYMMDD (repeatable). If omitted, pulls yesterday+today.")
    args = ap.parse_args()

    summary = run_espn_results_pull(db_path=args.db, dates=args.date, league="nba")
    for item in summary["per_date"]:
        print(f"date={item['date']} espn_events={item['espn_events']}")
    print(f"Total rows upserted: {summary['total_rows_upserted']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
