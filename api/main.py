from __future__ import annotations

from datetime import date as date_type
from typing import Optional, List, Any, Dict

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from src.db import connect
from src.pipelines.run_odds_snapshot import run_odds_snapshot
from src.transform.build_closing_lines import build_closing_lines
from src.transform.build_best_market_lines import build_best_market_lines
from src.pipelines.run_espn_results_pull import run_espn_results_pull
from src.transform.build_game_id_map import build_game_id_map
from src.transform.build_fact_game_results_best_market import build_fact_game_results_best_market
from src.transform.build_calibration_favorite import build_calibration_favorite


app = FastAPI(title="Sports Odds ETL API", version="0.1.0")


@app.get("/")
def root():
    return {"service": "sports-odds-etl-api", "health": "/health", "docs": "/docs"}


class OddsSnapshotRequest(BaseModel):
    sport: str = "basketball_nba"
    regions: str = "us"
    bookmakers: Optional[str] = None
    db: Optional[str] = None  # optional override; usually use DATABASE_URL


class SimpleJobRequest(BaseModel):
    db: Optional[str] = None


class EspnPullRequest(BaseModel):
    dates: Optional[List[str]] = None  # ["YYYYMMDD", ...]
    league: str = "nba"
    db: Optional[str] = None


class CalibrationRequest(BaseModel):
    step: float = 0.05
    db: Optional[str] = None


class ResultsRefreshRequest(BaseModel):
    dates: List[str]  # ["YYYY-MM-DD", ...]
    league: str = "nba"
    db: Optional[str] = None


def _rows_to_dicts(cur) -> List[Dict[str, Any]]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _db_target(override: Optional[str]) -> Optional[str]:
    return override


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/health")
def api_health():
    return {"ok": True}


from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

def _parse_iso_dt(s: str) -> datetime:
    # Handles "Z" and "+00:00"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    # If naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@app.get("/api/games/joined")
def api_games_joined(date: str = Query(..., description="YYYY-MM-DD (Chicago local day)")):
    try:
        day = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    chi = ZoneInfo("America/Chicago")
    start_local = datetime.combine(day, time.min).replace(tzinfo=chi)
    end_local = start_local + timedelta(days=1)

    con = connect()
    cur = con.cursor()

    # Pull candidates (small table, fine). If it grows, we can optimize later.
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
    rows = _rows_to_dicts(cur)

    filtered = []
    for r in rows:
        ct = r.get("commence_time")
        if not ct:
            continue
        try:
            dt_utc = _parse_iso_dt(ct)
            dt_local = dt_utc.astimezone(chi)
        except Exception:
            continue
        if start_local <= dt_local < end_local:
            filtered.append(r)

    return filtered


# Refresh endpoint for the React button
@app.post("/api/etl/results-refresh")
def api_results_refresh(req: ResultsRefreshRequest):
    yyyymmdd: List[str] = []
    for d in req.dates:
        try:
            dt = date_type.fromisoformat(d)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date: {d} (use YYYY-MM-DD)")
        yyyymmdd.append(dt.strftime("%Y%m%d"))

    try:
        pull_summary = run_espn_results_pull(
            db_path=req.db or None,
            dates=yyyymmdd,
            league=req.league,
        )
        mapped = build_game_id_map(_db_target(req.db))
        fact_rows = build_fact_game_results_best_market(_db_target(req.db))
        return {"pull": pull_summary, "mapped": mapped, "fact_rows": fact_rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/odds-snapshot")
def job_odds_snapshot(req: OddsSnapshotRequest):
    try:
        summary = run_odds_snapshot(
            db_path=req.db or None,
            sport=req.sport,
            regions=req.regions,
            bookmakers=req.bookmakers,
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/build-closing-lines")
def job_build_closing_lines(req: SimpleJobRequest):
    try:
        n = build_closing_lines(_db_target(req.db))
        return {"closing_rows": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/build-best-market-lines")
def job_build_best_market_lines(req: SimpleJobRequest):
    try:
        n = build_best_market_lines(_db_target(req.db))
        return {"best_market_rows": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/espn-results-pull")
def job_espn_results_pull(req: EspnPullRequest):
    try:
        summary = run_espn_results_pull(
            db_path=req.db or None,
            dates=req.dates,
            league=req.league,
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/build-game-id-map")
def job_build_game_id_map(req: SimpleJobRequest):
    try:
        n = build_game_id_map(_db_target(req.db))
        return {"mapped": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/build-fact-game-results-best-market")
def job_build_fact_game_results_best_market(req: SimpleJobRequest):
    try:
        n = build_fact_game_results_best_market(_db_target(req.db))
        return {"fact_rows": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/build-calibration-favorite")
def job_build_calibration_favorite(req: CalibrationRequest):
    try:
        n = build_calibration_favorite(_db_target(req.db), step=req.step)
        return {"calibration_rows": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/games/odds")
def api_games_odds(date: str = Query(..., description="YYYY-MM-DD (UTC date prefix)")):
    try:
        date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    con = connect()
    cur = con.cursor()

    sql = """
    SELECT
      event_id as odds_event_id,
      commence_time,
      home_team,
      away_team,
      best_home_price_american,
      best_away_price_american
    FROM fact_best_market_moneyline_odds
    WHERE commence_time LIKE ?
    ORDER BY commence_time
    """
    cur.execute(sql, (f"{date}%",))
    return _rows_to_dicts(cur)
