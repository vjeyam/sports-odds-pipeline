from __future__ import annotations

from datetime import date as date_type
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, HTTPException, Query
from zoneinfo import ZoneInfo

from api.utils.sql import rows_to_dicts
from api.utils.time import parse_iso_dt, profit_for_win_american
from src.db import connect

router = APIRouter(tags=["strategies"])

def _ph(con) -> str:
    # sqlite uses ?, psycopg uses %s
    return "%s" if con.__class__.__module__.startswith("psycopg") else "?"


def _pick_side(strat: str, fav: str, dog: str) -> str:
    if strat == "favorite":
        return fav
    if strat == "underdog":
        return dog
    if strat == "home":
        return "home"
    if strat == "away":
        return "away"
    raise ValueError("bad strategy")


def _implied_prob_from_american(odds: int) -> float:
    # implied probability (no vig removal)
    if odds < 0:
        a = abs(odds)
        return a / (a + 100.0)
    return 100.0 / (odds + 100.0)


@router.get("/api/strategies/summary")
def api_strategies_summary(
    start: str = Query(..., description="YYYY-MM-DD (Chicago local date)"),
    end: str = Query(..., description="YYYY-MM-DD (Chicago local date)"),
):
    """
    Summary stats computed directly from fact_game_results_best_market (not precomputed tables).
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
          winner,
          favorite_side,
          underdog_side,
          best_home_price_american,
          best_away_price_american
        FROM fact_game_results_best_market
        WHERE commence_time IS NOT NULL
        ORDER BY commence_time
        """
    )
    rows = rows_to_dicts(cur)

    games: List[Dict[str, Any]] = []
    for r in rows:
        ct = r.get("commence_time")
        if not ct:
            continue
        try:
            dt_local = parse_iso_dt(ct).astimezone(chi)
        except Exception:
            continue
        if start_day <= dt_local.date() <= end_day:
            games.append(r)

    strategies = ["favorite", "underdog", "home", "away"]

    out = []
    for strat in strategies:
        n_bets = 0
        wins = 0
        profit = 0.0

        for g in games:
            winner = g.get("winner")
            if winner not in ("home", "away"):
                continue

            home_ml = g.get("best_home_price_american")
            away_ml = g.get("best_away_price_american")
            if home_ml is None or away_ml is None:
                continue

            fav = g.get("favorite_side")
            dog = g.get("underdog_side")
            if fav not in ("home", "away") or dog not in ("home", "away"):
                continue

            picked = _pick_side(strat, fav, dog)
            odds = int(home_ml) if picked == "home" else int(away_ml)

            n_bets += 1
            if picked == winner:
                wins += 1
                profit += profit_for_win_american(odds)
            else:
                profit -= 1.0

        win_rate = (wins / n_bets) if n_bets else None
        roi = (profit / n_bets) if n_bets else None

        out.append(
            {
                "strategy": strat,
                "n_bets": n_bets,
                "wins": wins,
                "profit": profit if n_bets else None,
                "roi": roi,
                "win_rate": win_rate,
            }
        )

    return {"start": start_day.isoformat(), "end": end_day.isoformat(), "strategies": out}


@router.get("/api/strategies/equity")
def api_strategies_equity(
    strategy: str = Query(..., description="favorite|underdog|home|away"),
    start: str = Query(..., description="YYYY-MM-DD (Chicago local date)"),
    end: str = Query(..., description="YYYY-MM-DD (Chicago local date)"),
):
    """
    Equity curve points from fact_strategy_equity_curve (if present).
    Compatible with BOTH SQLite (?) and Postgres (%s) without dynamic SQL.
    """
    if strategy not in ("favorite", "underdog", "home", "away"):
        raise HTTPException(status_code=400, detail="strategy must be favorite|underdog|home|away")

    try:
        start_day = date_type.fromisoformat(start)
        end_day = date_type.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="start/end must be YYYY-MM-DD")
    if end_day < start_day:
        raise HTTPException(status_code=400, detail="end must be >= start")

    chi = ZoneInfo("America/Chicago")

    con = connect()
    try:
        cur = con.cursor()

        sql_sqlite = """
        SELECT
          game_index,
          commence_time,
          bet_profit,
          cum_profit,
          cum_roi,
          picked_side,
          winner,
          odds_american,
          odds_event_id,
          espn_event_id
        FROM fact_strategy_equity_curve
        WHERE strategy = ?
        ORDER BY game_index
        """

        sql_pg = """
        SELECT
          game_index,
          commence_time,
          bet_profit,
          cum_profit,
          cum_roi,
          picked_side,
          winner,
          odds_american,
          odds_event_id,
          espn_event_id
        FROM fact_strategy_equity_curve
        WHERE strategy = %s
        ORDER BY game_index
        """

        is_pg = con.__class__.__module__.startswith("psycopg")
        cur.execute(sql_pg if is_pg else sql_sqlite, (strategy,))
        rows = rows_to_dicts(cur)

        equity: List[Dict[str, Any]] = []
        for r in rows:
            ct = r.get("commence_time")
            if not ct:
                continue
            try:
                dt_local = parse_iso_dt(ct).astimezone(chi)
            except Exception:
                continue

            if start_day <= dt_local.date() <= end_day:
                equity.append(r)

        return {
            "strategy": strategy,
            "start": start_day.isoformat(),
            "end": end_day.isoformat(),
            "n_points": len(equity),
            "equity": equity,
        }

    finally:
        try:
            con.close()
        except Exception:
            pass


@router.get("/api/strategies/roi-buckets")
def api_strategies_roi_buckets(
    strategy: str = Query(..., description="favorite|underdog|home|away"),
    start: str = Query(..., description="YYYY-MM-DD (Chicago local date)"),
    end: str = Query(..., description="YYYY-MM-DD (Chicago local date)"),
    step: float = Query(0.05, ge=0.01, le=0.25, description="Bucket width (default 0.05)"),
    p_min: float = Query(0.40, ge=0.0, le=1.0, description="Minimum implied probability"),
    p_max: float = Query(0.80, ge=0.0, le=1.0, description="Maximum implied probability"),
):
    """
    ROI by implied probability bucket for a strategy.

    - Reads from fact_game_results_best_market
    - Includes only decided games (winner is home/away)
    - Uses $1 stake profit math (same as other endpoints)
    """
    if strategy not in ("favorite", "underdog", "home", "away"):
        raise HTTPException(status_code=400, detail="strategy must be favorite|underdog|home|away")

    try:
        start_day = date_type.fromisoformat(start)
        end_day = date_type.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="start/end must be YYYY-MM-DD")
    if end_day < start_day:
        raise HTTPException(status_code=400, detail="end must be >= start")
    if p_max <= p_min:
        raise HTTPException(status_code=400, detail="p_max must be > p_min")

    chi = ZoneInfo("America/Chicago")

    con = connect()
    cur = con.cursor()
    cur.execute(
        """
        SELECT
          commence_time,
          winner,
          favorite_side,
          underdog_side,
          best_home_price_american,
          best_away_price_american
        FROM fact_game_results_best_market
        WHERE commence_time IS NOT NULL
        ORDER BY commence_time
        """
    )
    rows = rows_to_dicts(cur)

    # Build bucket edges [p_min, p_min+step), ... up to p_max
    buckets: List[Tuple[float, float]] = []
    x = p_min
    while x < p_max - 1e-12:
        lo = round(x, 6)
        hi = round(min(x + step, p_max), 6)
        buckets.append((lo, hi))
        x += step

    # Stats per bucket
    stats: Dict[str, Dict[str, Any]] = {}
    for lo, hi in buckets:
        key = f"{lo:.2f}-{hi:.2f}"
        stats[key] = {
            "bucket": key,
            "bucket_lo": lo,
            "bucket_hi": hi,
            "n_bets": 0,
            "wins": 0,
            "profit": 0.0,
        }

    for r in rows:
        ct = r.get("commence_time")
        if not ct:
            continue

        try:
            dt_local = parse_iso_dt(ct).astimezone(chi)
        except Exception:
            continue

        if not (start_day <= dt_local.date() <= end_day):
            continue

        winner = r.get("winner")
        if winner not in ("home", "away"):
            continue

        home_ml = r.get("best_home_price_american")
        away_ml = r.get("best_away_price_american")
        if home_ml is None or away_ml is None:
            continue

        fav = r.get("favorite_side")
        dog = r.get("underdog_side")
        if fav not in ("home", "away") or dog not in ("home", "away"):
            continue

        picked = _pick_side(strategy, fav, dog)
        odds = int(home_ml) if picked == "home" else int(away_ml)
        p = _implied_prob_from_american(odds)

        if not (p_min <= p <= p_max):
            continue

        # Find bucket
        bucket_key = None
        for lo, hi in buckets:
            is_last = (hi == buckets[-1][1])
            if (lo <= p < hi) or (is_last and lo <= p <= hi):
                bucket_key = f"{lo:.2f}-{hi:.2f}"
                break
        if bucket_key is None:
            continue

        s = stats[bucket_key]
        s["n_bets"] += 1
        if picked == winner:
            s["wins"] += 1
            s["profit"] += profit_for_win_american(odds)
        else:
            s["profit"] -= 1.0

    out: List[Dict[str, Any]] = []
    for s in stats.values():
        n = int(s["n_bets"])
        wins = int(s["wins"])
        profit = float(s["profit"])
        out.append(
            {
                "bucket": s["bucket"],
                "bucket_lo": s["bucket_lo"],
                "bucket_hi": s["bucket_hi"],
                "n_bets": n,
                "wins": wins,
                "win_rate": (wins / n) if n else None,
                "profit": profit if n else None,
                "roi": (profit / n) if n else None,
            }
        )

    out.sort(key=lambda x: x["bucket_lo"])

    return {
        "strategy": strategy,
        "start": start_day.isoformat(),
        "end": end_day.isoformat(),
        "step": step,
        "p_min": p_min,
        "p_max": p_max,
        "n_bets_in_range": sum(int(x["n_bets"]) for x in out),
        "buckets": out,
    }
