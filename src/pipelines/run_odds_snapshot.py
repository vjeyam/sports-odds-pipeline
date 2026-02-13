from __future__ import annotations

import argparse
from datetime import datetime, timezone

from dotenv import load_dotenv

from src.extract.odds_api import fetch_odds_moneyline, print_quota_headers
from src.load.raw_odds_loader import flatten_moneyline, insert_raw_moneyline_rows
from src.transform.build_closing_lines import build_closing_lines
from src.transform.build_best_market_lines import build_best_market_lines


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main():
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="basketball_nba")
    ap.add_argument("--regions", default="us")
    ap.add_argument("--db", default="odds.sqlite")
    ap.add_argument("--bookmakers", default=None, help="optional comma-separated bookmaker keys")
    args = ap.parse_args()

    snapshot_ts = utc_now_iso()

    r, payload = fetch_odds_moneyline(
        sport_key=args.sport,
        regions=args.regions,
        bookmakers=args.bookmakers,
    )
    print_quota_headers(r)

    rows = flatten_moneyline(snapshot_ts, payload)
    inserted = insert_raw_moneyline_rows(args.db, rows)

    closing_rows = build_closing_lines(args.db)
    best_rows = build_best_market_lines(args.db)

    print(f"snapshot_ts={snapshot_ts}")
    print(f"events={len(payload)} rows_flattened={len(rows)} inserted_or_ignored={inserted}")
    print(f"closing_rows={closing_rows} best_market_rows={best_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
