from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.pipelines.run_espn_results_pull import run_espn_results_pull
from src.pipelines.run_full_pipeline import run_transforms
from src.quality.run_data_quality_checks import run_data_quality_checks


TZ = ZoneInfo("America/Chicago")


def chicago_today_yyyymmdd() -> str:
    return datetime.now(TZ).strftime("%Y%m%d")


def iter_dates(end_yyyymmdd: str, days: int) -> list[str]:
    end = datetime.strptime(end_yyyymmdd, "%Y%m%d").replace(tzinfo=TZ)
    start = end - timedelta(days=days - 1)
    out: list[str] = []
    cur = start
    while cur <= end:
        out.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill ESPN results (last N days) + run transforms + QC checks.")
    ap.add_argument("--db", default=os.getenv("DATABASE_URL") or "odds.sqlite")
    ap.add_argument("--days", type=int, default=7, help="Number of days to backfill ending at --end-date (inclusive).")
    ap.add_argument("--end-date", default=chicago_today_yyyymmdd(), help="End date YYYYMMDD in America/Chicago.")
    ap.add_argument("--stake", type=float, default=1.0)
    ap.add_argument("--calibration-step", type=float, default=0.05)
    ap.add_argument("--missing-results-hours", type=int, default=12)
    ap.add_argument("--fail-on-qc", action="store_true", help="Exit non-zero if QC fails thresholds.")
    args = ap.parse_args()

    db = args.db
    dates = iter_dates(args.end_date, args.days)

    print(f"[backfill] db={db}")
    print(f"[backfill] dates={dates[0]}..{dates[-1]} ({len(dates)} days)")

    # 1) Backfill ESPN results for each date
    total_upserted = 0
    for d in dates:
        summary = run_espn_results_pull(db_path=db, dates=[d], league="nba")
        upserted = int(summary.get("total_rows_upserted", 0))
        total_upserted += upserted
        print(f"[backfill] {d}: espn_rows={upserted}")

    print(f"[backfill] total_rows_upserted={total_upserted}")

    # 2) Run full transforms (includes game_id_map + joined fact tables + strategy layer)
    print("[transforms] running transforms...")
    run_transforms(db, stake=args.stake, calibration_step=args.calibration_step)
    print("[transforms] done")

    # 3) Run QC checks
    print("[qc] running data quality checks...")
    qc = run_data_quality_checks(db, missing_results_hours=args.missing_results_hours)

    for k, v in qc.items():
        print(f"[qc] {k}: {v}")

    if args.fail_on_qc and qc.get("qc_status") != "PASS":
        print("[qc] FAIL")
        return 2

    print("[done] backfill + qc complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
