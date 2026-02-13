from src.db import connect, ensure_schema


def build_closing_lines(db_path: str) -> int:
    conn = connect(db_path)
    ensure_schema(conn)

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
    conn.execute(sql)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM fact_closing_moneyline_odds").fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    n = build_closing_lines("odds.sqlite")
    print("closing_rows:", n)
