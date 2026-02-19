from __future__ import annotations

from datetime import date as date_type
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from zoneinfo import ZoneInfo

from api.utils.sql import rows_to_dicts
from api.utils.time import date_range_inclusive, parse_iso_dt, profit_for_win_american
from src.db import connect

router = APIRouter(tags=["analytics"])


@router.get("/api/analytics/summary")
def api_analytics_summary(
    start: str = Query(..., description="YYYY-MM-DD (Chicago local date)"),
    end: str = Query(..., description="YYYY-MM-DD (Chicago local date)"),
):
    """
    Analytics summary over a Chicago-local date range (inclusive).
    """
    try:
        start_day = date_type.fromisoformat(start)
        end_day = date_type.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="start/end must be YYYY-MM-DD")
    if end_day < start_day:
        raise HTTPException(status_code=400, detail="end must be >= start")

    chi = ZoneInfo("America/Chicago")

    con = connect()
    cur = con.cursor()

    cur.execute(
        """
        SELECT
          commence_time,
          best_home_price_american,
          best_away_price_american,
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
    present_dates: set[str] = set()

    for r in rows:
        ct = r.get("commence_time")
        if not ct:
            continue
        try:
            dt_local = parse_iso_dt(ct).astimezone(chi)
        except Exception:
            continue

        local_day = dt_local.date()
        if start_day <= local_day <= end_day:
            filtered.append(r)
            present_dates.add(local_day.isoformat())

    all_days = date_range_inclusive(start_day, end_day)
    missing_dates = [d.isoformat() for d in all_days if d.isoformat() not in present_dates]

    n_games = 0
    n_decided = 0
    fav_wins = 0
    dog_wins = 0
    fav_profit = 0.0
    dog_profit = 0.0

    for r in filtered:
        home_ml = r.get("best_home_price_american")
        away_ml = r.get("best_away_price_american")
        winner = r.get("winner")  # home/away or null
        fav_side = r.get("favorite_side")  # home/away or null
        dog_side = r.get("underdog_side")  # home/away or null

        if home_ml is None or away_ml is None:
            continue
        n_games += 1

        if winner not in ("home", "away"):
            continue
        if fav_side not in ("home", "away") or dog_side not in ("home", "away"):
            continue

        n_decided += 1

        fav_ml = home_ml if fav_side == "home" else away_ml
        dog_ml = home_ml if dog_side == "home" else away_ml

        if winner == fav_side:
            fav_wins += 1
            fav_profit += profit_for_win_american(int(fav_ml))
        else:
            fav_profit -= 1.0

        if winner == dog_side:
            dog_wins += 1
            dog_profit += profit_for_win_american(int(dog_ml))
        else:
            dog_profit -= 1.0

    favorite_win_rate = (fav_wins / n_decided) if n_decided else None
    underdog_win_rate = (dog_wins / n_decided) if n_decided else None
    favorite_roi = (fav_profit / n_decided) if n_decided else None
    underdog_roi = (dog_profit / n_decided) if n_decided else None

    return {
        "start": start_day.isoformat(),
        "end": end_day.isoformat(),
        "n_games_with_odds": n_games,
        "n_decided_games": n_decided,
        "favorite_win_rate": favorite_win_rate,
        "underdog_win_rate": underdog_win_rate,
        "favorite_profit": fav_profit if n_decided else None,
        "underdog_profit": dog_profit if n_decided else None,
        "favorite_roi": favorite_roi,
        "underdog_roi": underdog_roi,
        "missing_dates": missing_dates,
    }


@router.get("/api/analytics/daily")
def api_analytics_daily(
    start: str = Query(..., description="YYYY-MM-DD (Chicago local date)"),
    end: str = Query(..., description="YYYY-MM-DD (Chicago local date)"),
):
    """
    Daily analytics over a Chicago-local date range (inclusive).
    """
    try:
        start_day = date_type.fromisoformat(start)
        end_day = date_type.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="start/end must be YYYY-MM-DD")
    if end_day < start_day:
        raise HTTPException(status_code=400, detail="end must be >= start")

    chi = ZoneInfo("America/Chicago")

    con = connect()
    cur = con.cursor()

    cur.execute(
        """
        SELECT
          commence_time,
          best_home_price_american,
          best_away_price_american,
          winner,
          favorite_side,
          underdog_side
        FROM fact_game_results_best_market
        WHERE commence_time IS NOT NULL
        ORDER BY commence_time
        """
    )
    rows = rows_to_dicts(cur)

    stats: Dict[str, Dict[str, Any]] = {}
    present_dates: set[str] = set()

    def _ensure_day(d: str) -> Dict[str, Any]:
        if d not in stats:
            stats[d] = {
                "date": d,
                "n_games_with_odds": 0,
                "n_decided_games": 0,
                "favorite_wins": 0,
                "underdog_wins": 0,
                "favorite_profit": 0.0,
                "underdog_profit": 0.0,
            }
        return stats[d]

    for r in rows:
        ct = r.get("commence_time")
        if not ct:
            continue

        try:
            dt_local = parse_iso_dt(ct).astimezone(chi)
        except Exception:
            continue

        local_day = dt_local.date()
        if not (start_day <= local_day <= end_day):
            continue

        day_key = local_day.isoformat()
        present_dates.add(day_key)
        s = _ensure_day(day_key)

        home_ml = r.get("best_home_price_american")
        away_ml = r.get("best_away_price_american")
        winner = r.get("winner")
        fav_side = r.get("favorite_side")
        dog_side = r.get("underdog_side")

        if home_ml is None or away_ml is None:
            continue
        s["n_games_with_odds"] += 1

        if winner not in ("home", "away"):
            continue
        if fav_side not in ("home", "away") or dog_side not in ("home", "away"):
            continue

        s["n_decided_games"] += 1

        fav_ml = home_ml if fav_side == "home" else away_ml
        dog_ml = home_ml if dog_side == "home" else away_ml

        if winner == fav_side:
            s["favorite_wins"] += 1
            s["favorite_profit"] += profit_for_win_american(int(fav_ml))
        else:
            s["favorite_profit"] -= 1.0

        if winner == dog_side:
            s["underdog_wins"] += 1
            s["underdog_profit"] += profit_for_win_american(int(dog_ml))
        else:
            s["underdog_profit"] -= 1.0

    days = date_range_inclusive(start_day, end_day)
    daily: List[Dict[str, Any]] = []

    for d in days:
        key = d.isoformat()
        s = stats.get(key)
        if not s:
            daily.append(
                {
                    "date": key,
                    "n_games_with_odds": 0,
                    "n_decided_games": 0,
                    "favorite_win_rate": None,
                    "underdog_win_rate": None,
                    "favorite_profit": None,
                    "underdog_profit": None,
                    "favorite_roi": None,
                    "underdog_roi": None,
                }
            )
            continue

        n_decided = int(s["n_decided_games"])
        fav_wins = int(s["favorite_wins"])
        dog_wins = int(s["underdog_wins"])
        fav_profit = float(s["favorite_profit"])
        dog_profit = float(s["underdog_profit"])

        daily.append(
            {
                "date": key,
                "n_games_with_odds": int(s["n_games_with_odds"]),
                "n_decided_games": n_decided,
                "favorite_win_rate": (fav_wins / n_decided) if n_decided else None,
                "underdog_win_rate": (dog_wins / n_decided) if n_decided else None,
                "favorite_profit": fav_profit if n_decided else None,
                "underdog_profit": dog_profit if n_decided else None,
                "favorite_roi": (fav_profit / n_decided) if n_decided else None,
                "underdog_roi": (dog_profit / n_decided) if n_decided else None,
            }
        )

    missing_dates = [d.isoformat() for d in days if d.isoformat() not in present_dates]

    return {
        "start": start_day.isoformat(),
        "end": end_day.isoformat(),
        "missing_dates": missing_dates,
        "daily": daily,
    }