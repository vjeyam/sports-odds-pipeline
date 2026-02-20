from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Optional, Any

from dotenv import load_dotenv

_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(dotenv_path=_ENV_PATH)

from src.extract.odds_api import fetch_odds_moneyline, print_quota_headers
from src.load.raw_odds_loader import flatten_moneyline, insert_raw_moneyline_rows
from src.transform.build_closing_lines import build_closing_lines
from src.transform.build_best_market_lines import build_best_market_lines


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _get_odds_api_key() -> str:
    # Reload env in case caller started process without env loaded.
    # (No harm if already loaded.)
    load_dotenv(dotenv_path=_ENV_PATH, override=False)

    api_key = os.getenv("ODDS_API_KEY") or os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ODDS_API_KEY (or THE_ODDS_API_KEY) in environment")
    return api_key


# SQL constants (fixes psycopg type-checker complaints about dynamic strings)
ETL_RUN_LOG_DDL = """
CREATE TABLE IF NOT EXISTS etl_run_log (
  run_id TEXT PRIMARY KEY,
  pipeline TEXT NOT NULL,
  task TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT NOT NULL,
  status TEXT NOT NULL,
  snapshot_ts TEXT,
  sport TEXT,
  regions TEXT,
  bookmakers TEXT,
  events INTEGER,
  rows_flattened INTEGER,
  inserted_or_ignored INTEGER,
  closing_rows INTEGER,
  best_market_rows INTEGER,
  skipped INTEGER DEFAULT 0,
  git_sha TEXT,
  workflow_run_id TEXT,
  error_message TEXT
);
"""

ETL_RUN_LOG_INSERT_PG = """
INSERT INTO etl_run_log (
  run_id, pipeline, task, started_at, finished_at, status,
  snapshot_ts, sport, regions, bookmakers,
  events, rows_flattened, inserted_or_ignored, closing_rows, best_market_rows,
  skipped, git_sha, workflow_run_id, error_message
) VALUES (
  %s, %s, %s, %s, %s, %s,
  %s, %s, %s, %s,
  %s, %s, %s, %s, %s,
  %s, %s, %s, %s
);
"""

ETL_RUN_LOG_INSERT_SQLITE = """
INSERT INTO etl_run_log (
  run_id, pipeline, task, started_at, finished_at, status,
  snapshot_ts, sport, regions, bookmakers,
  events, rows_flattened, inserted_or_ignored, closing_rows, best_market_rows,
  skipped, git_sha, workflow_run_id, error_message
) VALUES (
  ?, ?, ?, ?, ?, ?,
  ?, ?, ?, ?,
  ?, ?, ?, ?, ?,
  ?, ?, ?, ?
);
"""


def _is_postgres_target(db_target: str) -> bool:
    return db_target.startswith("postgres://") or db_target.startswith("postgresql://")


def _ensure_etl_run_log(db_target: str) -> None:
    """
    Minimal run log table for 'production freshness' observability.
    Works for SQLite and Postgres (assumes src.db.connect can handle URL/path).
    """
    from src.db import connect, ensure_schema

    ensure_schema(db_target)

    with connect(db_target) as con:
        cur = con.cursor()
        cur.execute(ETL_RUN_LOG_DDL)
        con.commit()


def _insert_etl_run_log(db_target: str, row: dict[str, Any]) -> None:
    from src.db import connect

    values = (
        row.get("run_id"),
        row.get("pipeline"),
        row.get("task"),
        row.get("started_at"),
        row.get("finished_at"),
        row.get("status"),
        row.get("snapshot_ts"),
        row.get("sport"),
        row.get("regions"),
        row.get("bookmakers"),
        row.get("events"),
        row.get("rows_flattened"),
        row.get("inserted_or_ignored"),
        row.get("closing_rows"),
        row.get("best_market_rows"),
        row.get("skipped", 0),
        row.get("git_sha"),
        row.get("workflow_run_id"),
        row.get("error_message"),
    )

    sql = ETL_RUN_LOG_INSERT_PG if _is_postgres_target(db_target) else ETL_RUN_LOG_INSERT_SQLITE

    with connect(db_target) as con:
        cur = con.cursor()
        cur.execute(sql, values)
        con.commit()


def run_odds_snapshot(
    *,
    db_path: str | None = None,
    sport: str = "basketball_nba",
    regions: str = "us",
    bookmakers: Optional[str] = None,
    skip_if_no_events: bool = False,
) -> dict:
    import uuid

    started_at = utc_now_iso()
    snapshot_ts = started_at

    # Ensure key exists (and fail only when this function is called)
    _ = _get_odds_api_key()

    # DATABASE_URL overrides the sqlite file path (and also allows --db to be a URL)
    db_target = os.getenv("DATABASE_URL") or db_path or "odds.sqlite"

    # Ensure run log table exists
    _ensure_etl_run_log(db_target)

    git_sha = os.getenv("GITHUB_SHA")
    workflow_run_id = os.getenv("GITHUB_RUN_ID")

    run_id = str(uuid.uuid4())

    try:
        r, payload = fetch_odds_moneyline(
            sport_key=sport,
            regions=regions,
            bookmakers=bookmakers,
        )
        print_quota_headers(r)

        if skip_if_no_events and not payload:
            finished_at = utc_now_iso()
            summary = {
                "snapshot_ts": snapshot_ts,
                "sport": sport,
                "regions": regions,
                "bookmakers": bookmakers,
                "events": 0,
                "rows_flattened": 0,
                "inserted_or_ignored": 0,
                "closing_rows": 0,
                "best_market_rows": 0,
                "skipped": True,
            }
            _insert_etl_run_log(
                db_target,
                {
                    "run_id": run_id,
                    "pipeline": "odds_snapshot",
                    "task": "odds",
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "status": "success",
                    "snapshot_ts": snapshot_ts,
                    "sport": sport,
                    "regions": regions,
                    "bookmakers": bookmakers,
                    "events": 0,
                    "rows_flattened": 0,
                    "inserted_or_ignored": 0,
                    "closing_rows": 0,
                    "best_market_rows": 0,
                    "skipped": 1,
                    "git_sha": git_sha,
                    "workflow_run_id": workflow_run_id,
                    "error_message": None,
                },
            )
            return summary

        rows = flatten_moneyline(snapshot_ts, payload)
        inserted = insert_raw_moneyline_rows(db_target, rows)
        closing_rows = build_closing_lines(db_target)
        best_rows = build_best_market_lines(db_target)

        finished_at = utc_now_iso()

        summary = {
            "snapshot_ts": snapshot_ts,
            "sport": sport,
            "regions": regions,
            "bookmakers": bookmakers,
            "events": len(payload),
            "rows_flattened": len(rows),
            "inserted_or_ignored": inserted,
            "closing_rows": closing_rows,
            "best_market_rows": best_rows,
            "skipped": False,
        }

        _insert_etl_run_log(
            db_target,
            {
                "run_id": run_id,
                "pipeline": "odds_snapshot",
                "task": "odds",
                "started_at": started_at,
                "finished_at": finished_at,
                "status": "success",
                "snapshot_ts": snapshot_ts,
                "sport": sport,
                "regions": regions,
                "bookmakers": bookmakers,
                "events": len(payload),
                "rows_flattened": len(rows),
                "inserted_or_ignored": inserted,
                "closing_rows": closing_rows,
                "best_market_rows": best_rows,
                "skipped": 0,
                "git_sha": git_sha,
                "workflow_run_id": workflow_run_id,
                "error_message": None,
            },
        )

        return summary

    except Exception as e:
        finished_at = utc_now_iso()
        # Try to log failure, but don't mask original exception
        try:
            _insert_etl_run_log(
                db_target,
                {
                    "run_id": run_id,
                    "pipeline": "odds_snapshot",
                    "task": "odds",
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "status": "failed",
                    "snapshot_ts": snapshot_ts,
                    "sport": sport,
                    "regions": regions,
                    "bookmakers": bookmakers,
                    "events": None,
                    "rows_flattened": None,
                    "inserted_or_ignored": None,
                    "closing_rows": None,
                    "best_market_rows": None,
                    "skipped": 0,
                    "git_sha": git_sha,
                    "workflow_run_id": workflow_run_id,
                    "error_message": str(e),
                },
            )
        except Exception:
            pass
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="basketball_nba")
    ap.add_argument("--regions", default="us")
    ap.add_argument("--db", default="odds.sqlite")
    ap.add_argument("--bookmakers", default=None, help="optional comma-separated bookmaker keys")
    ap.add_argument(
        "--skip-if-no-events",
        action="store_true",
        help="If the API returns 0 events, exit successfully without transforms.",
    )
    args = ap.parse_args()

    summary = run_odds_snapshot(
        db_path=args.db,
        sport=args.sport,
        regions=args.regions,
        bookmakers=args.bookmakers,
        skip_if_no_events=args.skip_if_no_events,
    )

    print(
        f"snapshot_ts={summary['snapshot_ts']}\n"
        f"events={summary['events']} rows_flattened={summary['rows_flattened']} inserted_or_ignored={summary['inserted_or_ignored']}\n"
        f"closing_rows={summary['closing_rows']} best_market_rows={summary['best_market_rows']}"
        + (f"\nskipped={summary.get('skipped')}" if "skipped" in summary else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())