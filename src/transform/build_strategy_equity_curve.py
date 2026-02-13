from __future__ import annotations

import sqlite3
from typing import List, Tuple

from src.db import connect, ensure_schema


def bet_profit_from_american(odds: int, stake: float = 1.0) -> float:
    """Profit only (excluding returned stake)."""
    if odds < 0:
        return stake * (100.0 / abs(odds))
    return stake * (odds / 100.0)


def pick_side(strategy: str, favorite_side: str, underdog_side: str) -> str:
    if strategy == "favorite":
        return favorite_side
    if strategy == "underdog":
        return underdog_side
    if strategy == "home":
        return "home"
    if strategy == "away":
        return "away"
    raise ValueError(f"Unknown strategy: {strategy}")


def build_strategy_equity_curve(db_path: str, stake: float = 1.0) -> int:
    conn = connect(db_path)
    ensure_schema(conn)

    games = conn.execute("""
      SELECT
        odds_event_id,
        espn_event_id,
        commence_time,
        winner,
        favorite_side,
        underdog_side,
        best_home_price_american,
        best_away_price_american
      FROM fact_game_results_best_market
      WHERE winner IN ('home', 'away')
      ORDER BY commence_time
    """).fetchall()

    strategies = ["favorite", "underdog", "home", "away"]

    conn.execute("DELETE FROM fact_strategy_equity_curve")

    total_inserts = 0

    for strat in strategies:
        cum_profit = 0.0
        game_index = 0
        rows_to_insert: List[Tuple] = []

        for (
            odds_event_id,
            espn_event_id,
            commence_time,
            winner,
            favorite_side,
            underdog_side,
            home_odds,
            away_odds,
        ) in games:
            game_index += 1
            picked = pick_side(strat, favorite_side, underdog_side)

            odds = int(home_odds) if picked == "home" else int(away_odds)

            if picked == winner:
                p = bet_profit_from_american(odds, stake=stake)
            else:
                p = -stake

            cum_profit += p
            cum_roi = cum_profit / (game_index * stake) if game_index else 0.0

            rows_to_insert.append(
                (
                    strat,
                    game_index,
                    odds_event_id,
                    espn_event_id,
                    commence_time,
                    float(stake),
                    odds,
                    picked,
                    winner,
                    float(p),
                    float(cum_profit),
                    float(cum_roi),
                )
            )

        conn.executemany(
            """
            INSERT INTO fact_strategy_equity_curve (
              strategy, game_index,
              odds_event_id, espn_event_id, commence_time,
              stake, odds_american, picked_side, winner,
              bet_profit, cum_profit, cum_roi
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows_to_insert,
        )
        total_inserts += len(rows_to_insert)

    conn.commit()
    conn.close()
    return total_inserts


if __name__ == "__main__":
    n = build_strategy_equity_curve("odds.sqlite", stake=1.0)
    print("equity_rows_inserted:", n)
