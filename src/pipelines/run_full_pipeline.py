from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from src.transform.build_closing_lines import build_closing_lines
from src.transform.build_best_market_lines import build_best_market_lines
from src.transform.build_game_id_map import build_game_id_map
from src.transform.build_fact_game_results_best_market import build_fact_game_results_best_market
from src.transform.build_strategy_equity_curve import build_strategy_equity_curve
from src.transform.build_calibration_favorite import build_calibration_favorite
from src.transform.build_book_margin_summary import build_book_margin_summary
from src.transform.build_best_market_frequency import build_best_market_frequency
from src.transform.build_dashboard_kpis import build_dashboard_kpis


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class PipelineResult:
    db_path: str
    started_ts_utc: str
    finished_ts_utc: str | None = None

    closing_rows: int = 0
    best_market_rows: int = 0
    id_map_rows: int = 0
    results_best_market_rows: int = 0
    equity_rows: int = 0
    calibration_rows: int = 0
    book_margin_rows: int = 0
    best_market_freq_rows: int = 0
    kpis_written: int = 0


def run_transforms(
    db_path: str,
    *,
    stake: float = 1.0,
    calibration_step: float = 0.05,
) -> PipelineResult:
    """
    Builds/refreshes *dashboard-ready* fact tables from existing raw tables.

    Assumes you already ran:
      - run_odds_snapshot.py (raw_odds_moneyline populated)
      - run_espn_results_pull.py (raw_espn_game_results populated)

    Safe to run repeatedly (tables are rebuilt).
    """
    res = PipelineResult(db_path=db_path, started_ts_utc=utc_now_iso())

    # Odds-derived facts (safe even if already built by run_odds_snapshot)
    res.closing_rows = build_closing_lines(db_path)
    res.best_market_rows = build_best_market_lines(db_path)

    # Join odds <-> results via team match
    res.id_map_rows = build_game_id_map(db_path)

    # Game-level merged fact table (requires best-market odds + ESPN results + id map)
    res.results_best_market_rows = build_fact_game_results_best_market(db_path)

    # Strategy simulation facts
    res.equity_rows = build_strategy_equity_curve(db_path, stake=stake)

    # Calibration + market quality summaries
    res.calibration_rows = build_calibration_favorite(db_path, step=calibration_step)
    res.book_margin_rows = build_book_margin_summary(db_path)
    res.best_market_freq_rows = build_best_market_frequency(db_path)

    # Dashboard KPI key/values
    res.kpis_written = build_dashboard_kpis(db_path)

    res.finished_ts_utc = utc_now_iso()
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="odds.sqlite")
    ap.add_argument("--stake", type=float, default=1.0)
    ap.add_argument("--cal_step", type=float, default=0.05)
    args = ap.parse_args()

    res = run_transforms(args.db, stake=args.stake, calibration_step=args.cal_step)
    print(asdict(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
