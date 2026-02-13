from __future__ import annotations

import math
from typing import List, Tuple

from src.db import connect, ensure_schema


def american_to_implied_prob(odds: int) -> float:
    """
    Convert American odds to implied probability (no vig removal).
    +200 -> 100/(200+100) = 0.3333
    -245 -> 245/(245+100) = 0.7101
    """
    if odds is None:
        return float("nan")
    if odds < 0:
        return (-odds) / ((-odds) + 100.0)
    return 100.0 / (odds + 100.0)


def make_buckets(step: float = 0.05, lo: float = 0.50, hi: float = 1.00) -> List[Tuple[float, float, str]]:
    buckets = []
    x = lo
    while x < hi - 1e-9:
        a = round(x, 2)
        b = round(min(x + step, hi), 2)
        label = f"{a:.2f}-{b:.2f}"
        buckets.append((a, b, label))
        x += step
    return buckets


def build_calibration_favorite(db_path: str, step: float = 0.05) -> int:
    conn = connect(db_path)
    ensure_schema(conn)

    # Pull joined fact rows
    rows = conn.execute("""
      SELECT
        winner,
        favorite_side,
        best_home_price_american,
        best_away_price_american
      FROM fact_game_results_best_market
      WHERE winner IN ('home', 'away')
        AND favorite_side IN ('home', 'away')
        AND best_home_price_american IS NOT NULL
        AND best_away_price_american IS NOT NULL
    """).fetchall()

    # Compute per-game favorite implied prob and whether favorite won
    obs = []
    for winner, favorite_side, home_odds, away_odds in rows:
        home_p = american_to_implied_prob(int(home_odds))
        away_p = american_to_implied_prob(int(away_odds))

        fav_p = home_p if favorite_side == "home" else away_p
        fav_won = 1 if winner == favorite_side else 0

        # Guard against weird values
        if not (0.0 < fav_p < 1.0) or math.isnan(fav_p):
            continue

        obs.append((fav_p, fav_won))

    buckets = make_buckets(step=step)

    # Aggregate
    results = []
    for bmin, bmax, label in buckets:
        in_bucket = [(p, w) for (p, w) in obs if (p >= bmin and p < bmax) or (bmax >= 1.0 and p <= bmax and p >= bmin)]
        n = len(in_bucket)
        if n == 0:
            continue
        avg_p = sum(p for p, _ in in_bucket) / n
        win_rate = sum(w for _, w in in_bucket) / n
        diff = win_rate - avg_p
        results.append((label, bmin, bmax, n, win_rate, avg_p, diff))

    # Rebuild table
    conn.execute("DELETE FROM fact_calibration_favorite")
    conn.executemany("""
      INSERT INTO fact_calibration_favorite (
        bucket_label, bucket_min, bucket_max,
        n_games, favorite_win_rate, avg_implied_prob, diff_actual_minus_implied
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, results)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM fact_calibration_favorite").fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    n = build_calibration_favorite("odds.sqlite", step=0.05)
    print("calibration_buckets:", n)