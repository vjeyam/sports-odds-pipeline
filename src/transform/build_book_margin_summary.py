from __future__ import annotations

import math
from typing import List

from src.db import connect, ensure_schema


def american_to_implied_prob(odds: int) -> float:
    if odds is None:
        return float("nan")
    if odds < 0:
        return (-odds) / ((-odds) + 100.0)
    return 100.0 / (odds + 100.0)


def median(xs: List[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return float("nan")
    mid = n // 2
    if n % 2 == 1:
        return xs[mid]
    return (xs[mid - 1] + xs[mid]) / 2.0


def build_book_margin_summary(db_path: str) -> int:
    conn = connect(db_path)
    ensure_schema(conn)

    # Use closing lines per book (one row per game per book)
    rows = conn.execute("""
      SELECT bookmaker_key, home_price_american, away_price_american
      FROM fact_closing_moneyline_odds
      WHERE home_price_american IS NOT NULL
        AND away_price_american IS NOT NULL
    """).fetchall()

    by_book = {}
    for book, home_odds, away_odds in rows:
        ph = american_to_implied_prob(int(home_odds))
        pa = american_to_implied_prob(int(away_odds))
        if any(map(lambda x: (not (0.0 < x < 1.0)) or math.isnan(x), [ph, pa])):
            continue
        overround = (ph + pa) - 1.0
        by_book.setdefault(book, []).append(overround)

    results = []
    for book, ovs in by_book.items():
        ovs_sorted = sorted(ovs)
        n = len(ovs_sorted)
        results.append(
            (
                book,
                n,
                sum(ovs_sorted) / n,
                median(ovs_sorted),
                ovs_sorted[0],
                ovs_sorted[-1],
            )
        )

    conn.execute("DELETE FROM fact_book_margin_summary")
    conn.executemany("""
      INSERT INTO fact_book_margin_summary (
        bookmaker_key, n_games, avg_overround, median_overround, min_overround, max_overround
      ) VALUES (?, ?, ?, ?, ?, ?)
    """, results)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM fact_book_margin_summary").fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    n = build_book_margin_summary("odds.sqlite")
    print("books_summarized:", n)
