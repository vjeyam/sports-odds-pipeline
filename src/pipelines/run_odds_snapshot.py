from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

from src.extract.odds_api import fetch_odds_moneyline, print_quota_headers
from src.load.raw_odds_loader import flatten_moneyline, insert_raw_moneyline_rows
from src.transform.build_closing_lines import build_closing_lines
from src.transform.build_best_market_lines import build_best_market_lines


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_odds_snapshot(
    *,
    db_path: str | None = None,
    sport: str = "basketball_nba",
    regions: str = "us",
    bookmakers: Optional[str] = None,
) -> dict:
    load_dotenv()
    snapshot_ts = utc_now_iso()

    # DATABASE_URL overrides the sqlite file path (and also allows --db to be a URL)
    db_target = os.getenv("DATABASE_URL") or db_path

    r, payload = fetch_odds_moneyline(
        sport_key=sport,
        regions=regions,
        bookmakers=bookmakers,
    )
    print_quota_headers(r)

    rows = flatten_moneyline(snapshot_ts, payload)
    inserted = insert_raw_moneyline_rows(db_target, rows)
    closing_rows = build_closing_lines(db_target)
    best_rows = build_best_market_lines(db_target)

    return {
        "snapshot_ts": snapshot_ts,
        "sport": sport,
        "regions": regions,
        "bookmakers": bookmakers,
        "events": len(payload),
        "rows_flattened": len(rows),
        "inserted_or_ignored": inserted,
        "closing_rows": closing_rows,
        "best_market_rows": best_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="basketball_nba")
    ap.add_argument("--regions", default="us")
    ap.add_argument("--db", default="odds.sqlite")
    ap.add_argument("--bookmakers", default=None, help="optional comma-separated bookmaker keys")
    args = ap.parse_args()

    summary = run_odds_snapshot(
        db_path=args.db,
        sport=args.sport,
        regions=args.regions,
        bookmakers=args.bookmakers,
    )

    print(
        f"snapshot_ts={summary['snapshot_ts']}\n"
        f"events={summary['events']} rows_flattened={summary['rows_flattened']} inserted_or_ignored={summary['inserted_or_ignored']}\n"
        f"closing_rows={summary['closing_rows']} best_market_rows={summary['best_market_rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
