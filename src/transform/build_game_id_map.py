from __future__ import annotations

import re
from datetime import datetime, timezone

from src.db import connect, ensure_schema


def _is_postgres(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def norm_team(name: str | None) -> str:
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def build_game_id_map(db_target: str | None = None) -> int:
    conn = connect(db_target)
    ensure_schema(conn)

    is_pg = _is_postgres(conn)
    matched_ts = utc_now_iso()

    odds_sql = """
      SELECT event_id, home_team, away_team
      FROM fact_best_market_moneyline_odds
    """

    espn_sql = """
      SELECT espn_event_id, home_team, away_team
      FROM raw_espn_game_results
    """

    if is_pg:
        with conn.cursor() as cur:
            cur.execute(odds_sql)
            odds_games = cur.fetchall()
        with conn.cursor() as cur:
            cur.execute(espn_sql)
            espn_games = cur.fetchall()
    else:
        odds_games = conn.execute(odds_sql).fetchall()
        espn_games = conn.execute(espn_sql).fetchall()

    # Index ESPN by normalized (home, away)
    espn_index = {(norm_team(h), norm_team(a)): eid for (eid, h, a) in espn_games}

    mapped = 0

    if is_pg:
        upsert_sql = """
          INSERT INTO game_id_map
            (odds_event_id, espn_event_id, match_method, matched_ts)
          VALUES (%s, %s, %s, %s)
          ON CONFLICT (odds_event_id)
          DO UPDATE SET
            espn_event_id = EXCLUDED.espn_event_id,
            match_method  = EXCLUDED.match_method,
            matched_ts    = EXCLUDED.matched_ts
        """
        with conn.cursor() as cur:
            for odds_event_id, home, away in odds_games:
                key = (norm_team(home), norm_team(away))
                espn_event_id = espn_index.get(key)
                if espn_event_id is None:
                    continue
                cur.execute(upsert_sql, (odds_event_id, espn_event_id, "team_exact", matched_ts))
                mapped += 1
        conn.commit()
        conn.close()
        return mapped

    # SQLite
    for odds_event_id, home, away in odds_games:
        key = (norm_team(home), norm_team(away))
        espn_event_id = espn_index.get(key)
        if espn_event_id is None:
            continue

        conn.execute(
            """
            INSERT OR REPLACE INTO game_id_map
              (odds_event_id, espn_event_id, match_method, matched_ts)
            VALUES (?, ?, ?, ?)
            """,
            (odds_event_id, espn_event_id, "team_exact", matched_ts),
        )
        mapped += 1

    conn.commit()
    conn.close()
    return mapped


if __name__ == "__main__":
    n = build_game_id_map()
    print(f"Mapped {n} games")
