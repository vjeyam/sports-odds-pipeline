from __future__ import annotations

from datetime import date as date_type, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from api.utils.sql import rows_to_dicts
from api.utils.time import chicago_day_range, parse_iso_dt
from src.db import connect

router = APIRouter(tags=["games"])


def _is_postgres_conn(con) -> bool:
    return con.__class__.__module__.startswith("psycopg")


@router.get("/api/games/joined")
def api_games_joined(date: str = Query(..., description="YYYY-MM-DD (Chicago local day)")):
    """
    Reads from fact_game_results_best_market (already joined odds + results).
    Filters by Chicago-local day in Python (timezone-safe for SQLite/Postgres).
    """
    try:
        day = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    start_local, end_local, chi = chicago_day_range(day)

    con = connect()
    try:
        cur = con.cursor()
        cur.execute(
            """
            SELECT
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
            FROM fact_game_results_best_market
            WHERE commence_time IS NOT NULL
            ORDER BY commence_time
            """
        )
        rows = rows_to_dicts(cur)

        filtered: List[Dict[str, Any]] = []
        for r in rows:
            ct = r.get("commence_time")
            if not ct:
                continue
            try:
                dt_utc = parse_iso_dt(ct)
                dt_local = dt_utc.astimezone(chi)
            except Exception:
                continue
            if start_local <= dt_local < end_local:
                filtered.append(r)

        return filtered
    finally:
        try:
            con.close()
        except Exception:
            pass


@router.get("/games/odds")
def games_odds(date: str = Query(..., description="YYYY-MM-DD (UTC date prefix)")):
    """
    Pure odds endpoint (UTC prefix match on commence_time).
    Works on SQLite (LIKE ?) and Postgres (LIKE %s).
    """
    try:
        date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    con = connect()
    try:
        cur = con.cursor()
        is_pg = _is_postgres_conn(con)

        sql_sqlite = """
        SELECT
          event_id AS odds_event_id,
          commence_time,
          home_team,
          away_team,
          best_home_price_american,
          best_away_price_american
        FROM fact_best_market_moneyline_odds
        WHERE commence_time LIKE ?
        ORDER BY commence_time
        """

        sql_pg = """
        SELECT
          event_id AS odds_event_id,
          commence_time,
          home_team,
          away_team,
          best_home_price_american,
          best_away_price_american
        FROM fact_best_market_moneyline_odds
        WHERE commence_time LIKE %s
        ORDER BY commence_time
        """

        cur.execute(sql_pg if is_pg else sql_sqlite, (f"{date}%",))
        return rows_to_dicts(cur)
    finally:
        try:
            con.close()
        except Exception:
            pass


@router.get("/api/games/odds")
def api_games_odds(date: str = Query(..., description="YYYY-MM-DD (UTC date prefix)")):
    return games_odds(date)


@router.get("/api/games")
def api_games(date: str = Query(..., description="YYYY-MM-DD (Chicago local day)")):
    """
    Unified endpoint:
    - Always returns games (from best-market odds)
    - Adds results if they exist (left join)
    - Date is interpreted as Chicago local day (UI expectation)
    - IMPORTANT: scores only included when ESPN row is completed=1 OR status='In Progress'
    """
    try:
        day = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    start_local, end_local, chi = chicago_day_range(day)

    # Convert CT day bounds to UTC for a safe window prefilter in Python
    utc_start = start_local.astimezone(timezone.utc)
    utc_end = end_local.astimezone(timezone.utc)

    con = connect()
    try:
        cur = con.cursor()
        cur.execute(
            """
            SELECT
                o.event_id AS odds_event_id,
                o.commence_time,
                o.home_team,
                o.away_team,
                o.best_home_price_american,
                o.best_away_price_american,

                r.status AS status,
                r.completed AS completed,
                r.start_time AS start_time,

                CASE
                    WHEN r.completed = 1 OR r.status = 'In Progress' THEN r.home_score
                    ELSE NULL
                END AS home_score,

                CASE
                    WHEN r.completed = 1 OR r.status = 'In Progress' THEN r.away_score
                    ELSE NULL
                END AS away_score,

                CASE
                    WHEN r.completed = 1 AND r.home_score > r.away_score THEN o.home_team
                    WHEN r.completed = 1 AND r.away_score > r.home_score THEN o.away_team
                    ELSE NULL
                END AS winner

            FROM fact_best_market_moneyline_odds o
            LEFT JOIN game_id_map m ON o.event_id = m.odds_event_id
            LEFT JOIN (
                SELECT r1.*
                FROM raw_espn_game_results r1
                JOIN (
                    SELECT espn_event_id, MAX(pulled_ts) AS max_pulled_ts
                    FROM raw_espn_game_results
                    GROUP BY espn_event_id
                ) latest
                  ON r1.espn_event_id = latest.espn_event_id
                 AND r1.pulled_ts = latest.max_pulled_ts
            ) r
              ON m.espn_event_id = r.espn_event_id

            WHERE o.commence_time IS NOT NULL
            ORDER BY o.commence_time
            """
        )
        rows = rows_to_dicts(cur)

        filtered: List[Dict[str, Any]] = []
        for r in rows:
            ct = r.get("commence_time")
            if not ct:
                continue
            try:
                dt_utc = parse_iso_dt(ct)
            except Exception:
                continue

            # Fast UTC-window check first
            if not (utc_start <= dt_utc < utc_end):
                continue
            filtered.append(r)

        return filtered
    finally:
        try:
            con.close()
        except Exception:
            pass
