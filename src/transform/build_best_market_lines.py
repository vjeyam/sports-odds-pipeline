from __future__ import annotations

from src.db import connect, ensure_schema


def _is_postgres(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg")


def build_best_market_lines(db_target: str | None = None) -> int:
    conn = connect(db_target)
    ensure_schema(conn)

    is_pg = _is_postgres(conn)

    # Clear table
    if is_pg:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE fact_best_market_moneyline_odds;")
    else:
        conn.execute("DELETE FROM fact_best_market_moneyline_odds")

    sql = """
    INSERT INTO fact_best_market_moneyline_odds (
      event_id,
      commence_time, home_team, away_team,
      best_home_price_american, best_home_bookmaker_key,
      best_away_price_american, best_away_bookmaker_key
    )
    WITH base AS (
      SELECT
        event_id, commence_time, home_team, away_team, bookmaker_key,
        home_price_american, away_price_american
      FROM fact_closing_moneyline_odds
    ),
    best_home AS (
      SELECT b.*
      FROM base b
      JOIN (
        SELECT event_id, MAX(home_price_american) AS best_price
        FROM base
        GROUP BY event_id
      ) x
      ON b.event_id = x.event_id AND b.home_price_american = x.best_price
    ),
    best_away AS (
      SELECT b.*
      FROM base b
      JOIN (
        SELECT event_id, MAX(away_price_american) AS best_price
        FROM base
        GROUP BY event_id
      ) x
      ON b.event_id = x.event_id AND b.away_price_american = x.best_price
    )
    SELECT
      g.event_id,
      g.commence_time,
      g.home_team,
      g.away_team,

      (SELECT home_price_american FROM best_home bh WHERE bh.event_id = g.event_id ORDER BY bh.bookmaker_key LIMIT 1),
      (SELECT bookmaker_key       FROM best_home bh WHERE bh.event_id = g.event_id ORDER BY bh.bookmaker_key LIMIT 1),

      (SELECT away_price_american FROM best_away ba WHERE ba.event_id = g.event_id ORDER BY ba.bookmaker_key LIMIT 1),
      (SELECT bookmaker_key       FROM best_away ba WHERE ba.event_id = g.event_id ORDER BY ba.bookmaker_key LIMIT 1)

    FROM (SELECT DISTINCT event_id, commence_time, home_team, away_team FROM base) g
    ;
    """

    if is_pg:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fact_best_market_moneyline_odds")
            count = int(cur.fetchone()[0])
        conn.close()
        return count

    # SQLite
    conn.execute(sql)
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM fact_best_market_moneyline_odds").fetchone()[0]
    conn.close()
    return int(count)


if __name__ == "__main__":
    n = build_best_market_lines()
    print("best_market_rows:", n)
