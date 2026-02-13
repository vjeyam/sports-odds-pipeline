from src.db import connect, ensure_schema


def build_fact_game_results_best_market(db_path: str) -> int:
    conn = connect(db_path)
    ensure_schema(conn)

    conn.execute("DELETE FROM fact_game_results_best_market")

    sql = """
    INSERT INTO fact_game_results_best_market (
      odds_event_id,
      espn_event_id,
      commence_time,
      home_team,
      away_team,
      best_home_price_american,
      best_away_price_american,
      home_score,
      away_score,
      winner,
      favorite_side,
      underdog_side
    )
    SELECT
      o.event_id,
      m.espn_event_id,
      o.commence_time,
      o.home_team,
      o.away_team,
      o.best_home_price_american,
      o.best_away_price_american,
      r.home_score,
      r.away_score,

      CASE
        WHEN r.home_score > r.away_score THEN 'home'
        WHEN r.away_score > r.home_score THEN 'away'
        ELSE NULL
      END AS winner,

      CASE
        WHEN o.best_home_price_american < o.best_away_price_american THEN 'home'
        ELSE 'away'
      END AS favorite_side,

      CASE
        WHEN o.best_home_price_american < o.best_away_price_american THEN 'away'
        ELSE 'home'
      END AS underdog_side

    FROM fact_best_market_moneyline_odds o
    JOIN game_id_map m
      ON o.event_id = m.odds_event_id
    JOIN raw_espn_game_results r
      ON m.espn_event_id = r.espn_event_id
    WHERE r.completed = 1
    ;
    """

    conn.execute(sql)
    conn.commit()

    count = conn.execute(
        "SELECT COUNT(*) FROM fact_game_results_best_market"
    ).fetchone()[0]

    conn.close()
    return count


if __name__ == "__main__":
    n = build_fact_game_results_best_market("odds.sqlite")
    print("fact_rows:", n)
