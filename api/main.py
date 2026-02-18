from __future__ import annotations

from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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


def _db_target(override: Optional[str]) -> Optional[str]:
    # If caller provides db override, use it.
    # Else allow src.db.connect() to use DATABASE_URL or fallback.
    return override


@app.get("/health")
def health():
    return {"ok": True}


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
        # build_calibration_favorite(db_target=None, step=...) after your refactor
        n = build_calibration_favorite(_db_target(req.db), step=req.step)
        return {"calibration_rows": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
