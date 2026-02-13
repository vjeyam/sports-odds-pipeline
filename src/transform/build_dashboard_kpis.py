from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from src.db import connect, ensure_schema


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_dashboard_kpis(db_path: str) -> int:
    conn = connect(db_path)
    ensure_schema(conn)

    kpis: Dict[str, str] = {}

    # Total games + favorite win rate
    total_games = conn.execute("""
      SELECT COUNT(*) FROM fact_game_results_best_market
      WHERE winner IN ('home','away')
    """).fetchone()[0] or 0
    kpis["total_games"] = str(total_games)

    fav_wins = conn.execute("""
      SELECT COUNT(*) FROM fact_game_results_best_market
      WHERE winner = favorite_side
        AND winner IN ('home','away')
        AND favorite_side IN ('home','away')
    """).fetchone()[0] or 0

    fav_win_rate = (fav_wins / total_games) if total_games else 0.0
    kpis["favorite_win_rate"] = f"{fav_win_rate:.6f}"

    # Avg overround (vig) across books (simple unweighted avg of book avgs)
    avg_vig = conn.execute("""
      SELECT AVG(avg_overround) FROM fact_book_margin_summary
    """).fetchone()[0]
    kpis["avg_overround_across_books"] = f"{(avg_vig or 0.0):.6f}"

    # Calibration weighted MAE across buckets
    # MAE = average |actual - implied| weighted by bucket n_games
    cal = conn.execute("""
      SELECT
        SUM(ABS(diff_actual_minus_implied) * n_games) AS weighted_abs_err,
        SUM(n_games) AS total_n
      FROM fact_calibration_favorite
    """).fetchone()
    weighted_abs_err = cal[0] or 0.0
    total_n = cal[1] or 0
    cal_mae = (weighted_abs_err / total_n) if total_n else 0.0
    kpis["calibration_weighted_mae"] = f"{cal_mae:.6f}"

    # Strategy ROI + net profit (take last point in equity curve per strategy)
    strat_rows = conn.execute("""
      SELECT strategy, cum_profit, cum_roi
      FROM fact_strategy_equity_curve
      WHERE (strategy, game_index) IN (
        SELECT strategy, MAX(game_index)
        FROM fact_strategy_equity_curve
        GROUP BY strategy
      )
    """).fetchall()

    for strat, cum_profit, cum_roi in strat_rows:
        kpis[f"roi_{strat}"] = f"{(cum_roi or 0.0):.6f}"
        kpis[f"net_profit_{strat}"] = f"{(cum_profit or 0.0):.6f}"

    # Last refresh time
    kpis["kpis_built_ts_utc"] = utc_now_iso()

    # Write table
    conn.execute("DELETE FROM fact_dashboard_kpis")
    conn.executemany(
        "INSERT INTO fact_dashboard_kpis (kpi_name, kpi_value) VALUES (?, ?)",
        list(kpis.items()),
    )
    conn.commit()
    conn.close()

    return len(kpis)


if __name__ == "__main__":
    n = build_dashboard_kpis("odds.sqlite")
    print("kpis_written:", n)
