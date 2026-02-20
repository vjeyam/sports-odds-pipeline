from __future__ import annotations

from typing import List, Tuple

from src.db import connect, ensure_schema


def bet_profit_from_american(odds: int, stake: float = 1.0) -> float:
    """Profit only (excluding returned stake)."""
    if odds < 0:
        return stake * (100.0 / abs(float(odds)))
    return stake * (float(odds) / 100.0)


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


def _is_postgres_conn(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg")


def build_strategy_equity_curve(db_path: str, stake: float = 1.0) -> int:
    """
    Builds fact_strategy_equity_curve for each strategy.

    Works for BOTH:
      - SQLite (sqlite3): placeholder "?"
      - Postgres (psycopg v3): placeholder "%s"

    Rebuilds the table each run.
    """
    conn = connect(db_path)
    ensure_schema(conn)

    is_pg = _is_postgres_conn(conn)
    ph = "%s" if is_pg else "?"

    select_sql = """
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
    """

    insert_sql = f"""
      INSERT INTO fact_strategy_equity_curve (
        strategy, game_index,
        odds_event_id, espn_event_id, commence_time,
        stake, odds_american, picked_side, winner,
        bet_profit, cum_profit, cum_roi
      ) VALUES (
        {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}
      )
    """

    # Postgres upsert (SQLite has its own ON CONFLICT too, but placeholder differences make it simpler to split)
    if is_pg:
        insert_sql += """
        ON CONFLICT (strategy, odds_event_id) DO UPDATE SET
          game_index = EXCLUDED.game_index,
          espn_event_id = EXCLUDED.espn_event_id,
          commence_time = EXCLUDED.commence_time,
          stake = EXCLUDED.stake,
          odds_american = EXCLUDED.odds_american,
          picked_side = EXCLUDED.picked_side,
          winner = EXCLUDED.winner,
          bet_profit = EXCLUDED.bet_profit,
          cum_profit = EXCLUDED.cum_profit,
          cum_roi = EXCLUDED.cum_roi
        """

    cur = conn.cursor()
    try:
        cur.execute(select_sql)
        games = cur.fetchall()

        cur.execute("DELETE FROM fact_strategy_equity_curve")

        strategies = ["favorite", "underdog", "home", "away"]
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
                    p = -float(stake)

                cum_profit += p
                cum_roi = cum_profit / (game_index * float(stake)) if game_index else 0.0

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

            if rows_to_insert:
                cur.executemany(insert_sql, rows_to_insert)
                total_inserts += len(rows_to_insert)

        conn.commit()
        return total_inserts

    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


if __name__ == "__main__":
    n = build_strategy_equity_curve("odds.sqlite", stake=1.0)
    print("equity_rows_inserted:", n)
