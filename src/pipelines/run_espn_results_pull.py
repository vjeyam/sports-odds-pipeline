from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.extract.espn_api import fetch_nba_scoreboard
from src.load.raw_results_loader import flatten_espn_scoreboard, upsert_raw_espn_results


TZ = ZoneInfo("America/Chicago")


def default_dates() -> list[str]:
    today_local = datetime.now(TZ).date()
    yday_local = today_local - timedelta(days=1)
    return [yday_local.strftime("%Y%m%d"), today_local.strftime("%Y%m%d")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="odds.sqlite")
    ap.add_argument("--date", action="append", help="YYYYMMDD (repeatable). If omitted, pulls yesterday+today.")
    args = ap.parse_args()
    
    dates = args.date if args.date else default_dates()
    
    total_rows = 0
    for d in dates:
        payload = fetch_nba_scoreboard(d)
        rows = flatten_espn_scoreboard(d, payload, league="nba")
        upsert_raw_espn_results(args.db, rows)
        print(f"date={d} espn_events={len(rows)}")
        total_rows += len(rows)
        
    print(f"Total rows upserted: {total_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())