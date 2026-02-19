from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.deps import db_target
from api.models import CalibrationRequest, EspnPullRequest, OddsSnapshotRequest, SimpleJobRequest
from src.pipelines.run_espn_results_pull import run_espn_results_pull
from src.pipelines.run_odds_snapshot import run_odds_snapshot
from src.transform.build_best_market_lines import build_best_market_lines
from src.transform.build_calibration_favorite import build_calibration_favorite
from src.transform.build_closing_lines import build_closing_lines
from src.transform.build_fact_game_results_best_market import build_fact_game_results_best_market
from src.transform.build_game_id_map import build_game_id_map
from src.transform.build_strategy_equity_curve import build_strategy_equity_curve

router = APIRouter(tags=["jobs"])


@router.post("/jobs/odds-snapshot")
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


@router.post("/jobs/build-closing-lines")
def job_build_closing_lines(req: SimpleJobRequest):
    try:
        n = build_closing_lines(db_target(req.db))
        return {"closing_rows": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/build-best-market-lines")
def job_build_best_market_lines(req: SimpleJobRequest):
    try:
        n = build_best_market_lines(db_target(req.db))
        return {"best_market_rows": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/espn-results-pull")
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


@router.post("/jobs/build-game-id-map")
def job_build_game_id_map(req: SimpleJobRequest):
    try:
        n = build_game_id_map(db_target(req.db))
        return {"mapped": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/build-fact-game-results-best-market")
def job_build_fact_game_results_best_market(req: SimpleJobRequest):
    try:
        n = build_fact_game_results_best_market(db_target(req.db))
        return {"fact_rows": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/build-calibration-favorite")
def job_build_calibration_favorite(req: CalibrationRequest):
    try:
        n = build_calibration_favorite(db_target(req.db), step=req.step)
        return {"calibration_rows": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/build-strategy-equity-curve")
def job_build_strategy_equity_curve(req: SimpleJobRequest):
    """
    Optional manual job endpoint to rebuild strategy equity curve.
    """
    try:
        n = build_strategy_equity_curve(db_target(req.db), stake=1.0)
        return {"equity_rows": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))