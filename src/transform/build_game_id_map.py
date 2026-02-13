from __future__ import annotations

import re
from datetime import datetime, timezone

from src.db import connect, ensure_schema


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def norm_team(name: str | None) -> str:
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def build_game_id_map(db_path: str) -> int:
    conn = connect(db_path)
    ensure_schema(conn)

    matched_ts = utc_now_iso()
    
    # Odds games (one row per odds event)
    odds_games = conn.execute("""
      SELECT event_id, home_team, away_team
      FROM fact_best_market_moneyline_odds
    """).fetchall()
    
    # ESPN results that we have
    espn_games = conn.execute("""
      SELECT espn_event_id, home_team, away_team
      FROM raw_espn_game_results
    """).fetchall()
    
    # Index ESPN by normalized (home, away)
    espn_index = {(norm_team(h), norm_team(a)): eid for (eid, h, a) in espn_games}
    
    mapped = 0
    for odds_event_id, home, away in odds_games:
        key = (norm_team(home), norm_team(away))
        espn_event_id = espn_index.get(key)
        if espn_event_id is None:
            continue
        
        conn.execute("""
          INSERT OR REPLACE INTO game_id_map
            (odds_event_id, espn_event_id, match_method, matched_ts)
          VALUES (?, ?, ?, ?)
        """, (odds_event_id, espn_event_id, "team_exact", matched_ts))

        mapped += 1
        
    conn.commit()
    conn.close()
    return mapped


if __name__ == "__main__":
    n = build_game_id_map("odds.sqlite")
    print(f"Mapped {n} games")