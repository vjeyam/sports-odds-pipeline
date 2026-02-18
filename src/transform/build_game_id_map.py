from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, List

from src.db import connect, ensure_schema


def _is_postgres(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


_TEAM_ALIASES = {
    "la lakers": "los angeles lakers",
    "l a lakers": "los angeles lakers",
    "la clippers": "los angeles clippers",
    "l a clippers": "los angeles clippers",
    "trail blazers": "portland trail blazers",
    "blazers": "portland trail blazers",
    "sixers": "philadelphia 76ers",
    "76ers": "philadelphia 76ers",
}


def norm_team(name: str | None) -> str:
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    s = re.sub(r"\s+", " ", s)
    return _TEAM_ALIASES.get(s, s)


def build_game_id_map(db_target: str | None = None) -> int:
    conn = connect(db_target)
    ensure_schema(conn)

    is_pg = _is_postgres(conn)
    matched_ts = utc_now_iso()

    # Odds: best-market per event (should be one row per event_id)
    odds_sql = """
      SELECT event_id, home_team, away_team, commence_time
      FROM fact_best_market_moneyline_odds
    """

    # ESPN: results per espn_event_id (may include multiple scoreboard dates)
    # Note: ESPN time column is start_time (NOT commence_time)
    espn_sql = """
      SELECT espn_event_id, home_team, away_team, start_time
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

    # Index ESPN:
    #  - directional (home, away)
    #  - team_set (ignore direction)
    espn_dir: Dict[Tuple[str, str], List[Tuple[str, Optional[str]]]] = {}
    espn_set: Dict[Tuple[str, str], List[Tuple[str, Optional[str]]]] = {}

    for (eid, h, a, st) in espn_games:
        nh, na = norm_team(h), norm_team(a)
        espn_dir.setdefault((nh, na), []).append((eid, st))
        espn_set.setdefault(tuple(sorted([nh, na])), []).append((eid, st))

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
            for odds_event_id, home, away, _odds_ct in odds_games:
                nh, na = norm_team(home), norm_team(away)

                # A) exact directional
                cands = espn_dir.get((nh, na))
                method = "team_exact"

                # B) swapped directional
                if not cands:
                    cands = espn_dir.get((na, nh))
                    method = "team_swapped"

                # C) team set (ignore direction)
                if not cands:
                    cands = espn_set.get(tuple(sorted([nh, na])))
                    method = "team_set"

                if not cands:
                    continue

                espn_event_id = cands[0][0]
                cur.execute(upsert_sql, (odds_event_id, espn_event_id, method, matched_ts))
                mapped += 1

        conn.commit()
        conn.close()
        return mapped

    # SQLite
    for odds_event_id, home, away, _odds_ct in odds_games:
        nh, na = norm_team(home), norm_team(away)

        cands = espn_dir.get((nh, na))
        method = "team_exact"

        if not cands:
            cands = espn_dir.get((na, nh))
            method = "team_swapped"

        if not cands:
            cands = espn_set.get(tuple(sorted([nh, na])))
            method = "team_set"

        if not cands:
            continue

        espn_event_id = cands[0][0]

        conn.execute(
            """
            INSERT OR REPLACE INTO game_id_map
              (odds_event_id, espn_event_id, match_method, matched_ts)
            VALUES (?, ?, ?, ?)
            """,
            (odds_event_id, espn_event_id, method, matched_ts),
        )
        mapped += 1

    conn.commit()
    conn.close()
    return mapped


if __name__ == "__main__":
    n = build_game_id_map()
    print(f"Mapped {n} games")
