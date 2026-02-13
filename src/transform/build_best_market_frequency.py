from __future__ import annotations

from src.db import connect, ensure_schema


def build_best_market_frequency(db_path: str) -> int:
    conn = connect(db_path)
    ensure_schema(conn)

    # Count best-home and best-away occurrences
    rows = conn.execute("""
      SELECT best_home_bookmaker_key, best_away_bookmaker_key
      FROM fact_best_market_moneyline_odds
      WHERE best_home_bookmaker_key IS NOT NULL
        AND best_away_bookmaker_key IS NOT NULL
    """).fetchall()

    counts = {}
    total_slots = 0  # 2 per game (home + away)
    for bh, ba in rows:
        counts[bh] = counts.get(bh, {"home": 0, "away": 0})  # ensure exists
        counts[ba] = counts.get(ba, {"home": 0, "away": 0})
        counts[bh]["home"] += 1
        counts[ba]["away"] += 1
        total_slots += 2

    results = []
    for book, d in counts.items():
        home_ct = d["home"]
        away_ct = d["away"]
        total_ct = home_ct + away_ct
        share = (total_ct / total_slots) if total_slots else 0.0
        results.append((book, home_ct, away_ct, total_ct, share))

    conn.execute("DELETE FROM fact_best_market_frequency")
    conn.executemany("""
      INSERT INTO fact_best_market_frequency (
        bookmaker_key, best_home_count, best_away_count, best_total_count, best_share
      ) VALUES (?, ?, ?, ?, ?)
    """, results)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM fact_best_market_frequency").fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    n = build_best_market_frequency("odds.sqlite")
    print("books_counted:", n)
