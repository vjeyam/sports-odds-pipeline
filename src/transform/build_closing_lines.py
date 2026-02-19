from __future__ import annotations

from src.db import connect, ensure_schema


def _is_postgres(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg")


def build_closing_lines(db_target: str | None = None) -> int:
    conn = connect(db_target)
    ensure_schema(conn)

    is_pg = _is_postgres(conn)

    # Clear table
    if is_pg:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE fact_closing_moneyline_odds;")
    else:
        conn.execute("DELETE FROM fact_closing_moneyline_odds")

    sql = """
    INSERT INTO fact_closing_moneyline_odds (
      event_id,
      bookmaker_key,
      snapshot_ts,
      commence_time,
      home_team,
      away_team,
      home_price_american,
      away_price_american
    )
    WITH latest AS (
      SELECT
        event_id,
        bookmaker_key,
        MAX(snapshot_ts) AS snapshot_ts
      FROM raw_moneyline_odds
      WHERE commence_time IS NOT NULL
        AND snapshot_ts <= commence_time
      GROUP BY event_id, bookmaker_key
    )
    SELECT
      r.event_id,
      r.bookmaker_key,
      r.snapshot_ts,
      r.commence_time,
      r.home_team,
      r.away_team,
      MAX(CASE WHEN r.outcome_name = r.home_team THEN r.outcome_price_american END) AS home_price_american,
      MAX(CASE WHEN r.outcome_name = r.away_team THEN r.outcome_price_american END) AS away_price_american
    FROM raw_moneyline_odds r
    JOIN latest l
      ON r.event_id = l.event_id
     AND r.bookmaker_key = l.bookmaker_key
     AND r.snapshot_ts = l.snapshot_ts
    GROUP BY
      r.event_id, r.bookmaker_key, r.snapshot_ts,
      r.commence_time, r.home_team, r.away_team
    ;
    """

    if is_pg:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fact_closing_moneyline_odds")
            count = int(cur.fetchone()[0])
        conn.close()
        return count

    # SQLite
    conn.execute(sql)
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM fact_closing_moneyline_odds").fetchone()[0]
    conn.close()
    return int(count)


if __name__ == "__main__":
    n = build_closing_lines()
    print("closing_rows:", n)
