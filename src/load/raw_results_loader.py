from __future__ import annotations

from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone

from src.db import connect, ensure_schema


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def flatten_espn_scoreboard(scoreboard_date: str, payload: Dict[str, Any], league: str = "nba") -> List[Tuple]:
    """
    Flatten ESPN scoreboard JSON into rows for raw_espn_game_results.

    Extracts:
      - espn_event_id
      - start_time (competition date preferred)
      - status text
      - completed flag
      - home/away team names + scores
    """
    pulled_ts = utc_now_iso()
    rows: List[Tuple] = []

    events = payload.get("events") or []
    for ev in events:
        event_id = ev.get("id")
        if not event_id:
            continue

        # Prefer competition-level date; fall back to event date
        competitions = ev.get("competitions") or []
        comp0 = competitions[0] if competitions else {}
        start_time = comp0.get("date") or ev.get("date")

        # Competitors (teams + scores)
        competitors = comp0.get("competitors") or []
        home_team = away_team = None
        home_score = away_score = None

        for c in competitors:
            ha = c.get("homeAway")
            team_obj = c.get("team") or {}
            team = team_obj.get("displayName") or team_obj.get("name")

            score_raw = c.get("score")
            try:
                score = int(score_raw) if score_raw is not None else None
            except (TypeError, ValueError):
                score = None

            if ha == "home":
                home_team, home_score = team, score
            elif ha == "away":
                away_team, away_score = team, score

        # Status / completed
        status_type = ((ev.get("status") or {}).get("type")) or {}

        status_text = (
            status_type.get("shortDetail")
            or status_type.get("detail")
            or status_type.get("description")
            or status_type.get("state")
        )

        completed_val = status_type.get("completed")
        completed = 1 if completed_val in (True, "true", "True", 1, "1") else 0

        # Extra fallbacks: ESPN often uses state="post" for completed games
        state = status_type.get("state")
        if completed == 0 and state == "post":
            completed = 1

        # If text contains "Final", treat as completed
        if completed == 0 and isinstance(status_text, str) and "final" in status_text.lower():
            completed = 1

        rows.append(
            (
                scoreboard_date,
                event_id,
                league,
                pulled_ts,
                start_time,
                status_text,
                completed,
                home_team,
                away_team,
                home_score,
                away_score,
            )
        )

    return rows


def upsert_raw_espn_results(db_path: str, rows: List[Tuple]) -> int:
    conn = connect(db_path)
    ensure_schema(conn)

    sql = """
    INSERT OR REPLACE INTO raw_espn_game_results (
      scoreboard_date, espn_event_id, league, pulled_ts,
      start_time, status, completed,
      home_team, away_team, home_score, away_score
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    cursor = conn.cursor()
    cursor.executemany(sql, rows)
    conn.commit()
    
    # Recount rows after upsert
    num = cursor.rowcount
    conn.close()
    
    return num