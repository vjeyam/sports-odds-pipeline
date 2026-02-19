from __future__ import annotations

import traceback
from datetime import date as date_type
from typing import List

from fastapi import APIRouter, HTTPException

from api.deps import db_target
from api.models import OddsRefreshRequest, ResultsRefreshRequest
from src.pipelines.run_espn_results_pull import run_espn_results_pull
from src.pipelines.run_odds_snapshot import run_odds_snapshot
from src.transform.build_best_market_lines import build_best_market_lines
from src.transform.build_closing_lines import build_closing_lines
from src.transform.build_fact_game_results_best_market import build_fact_game_results_best_market
from src.transform.build_game_id_map import build_game_id_map
from src.transform.build_strategy_equity_curve import build_strategy_equity_curve

router = APIRouter(tags=["etl"])


@router.post("/api/etl/results-refresh")
def api_results_refresh(req: ResultsRefreshRequest):
    """
    Button-driven refresh:
    - converts YYYY-MM-DD -> ESPN scoreboard YYYYMMDD
    - pulls ESPN rows
    - rebuilds mapping + fact join table
    - ALSO rebuilds fact_strategy_equity_curve (auto, so it doesn't get stale)
    """
    yyyymmdd: List[str] = []
    for d in req.dates:
        try:
            dt = date_type.fromisoformat(d)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date: {d} (use YYYY-MM-DD)")
        yyyymmdd.append(dt.strftime("%Y%m%d"))

    try:
        db_path = db_target(req.db)

        pull_summary = run_espn_results_pull(
            db_path=db_path,
            dates=yyyymmdd,
            league=req.league,
        )

        mapped = build_game_id_map(db_path)
        fact_rows = build_fact_game_results_best_market(db_path)

        # rebuild strategy curve after results are refreshed
        equity_rows = build_strategy_equity_curve(db_path, stake=1.0)

        return {
            "pull": pull_summary,
            "mapped": mapped,
            "fact_rows": fact_rows,
            "equity_rows": equity_rows,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/etl/odds-refresh")
def api_odds_refresh(req: OddsRefreshRequest):
    """
    Refresh odds snapshot + rebuild derived tables used by /api/games.
    """
    try:
        db_path = db_target(req.db)

        snap = run_odds_snapshot(
            db_path=db_path,
            sport=req.sport,
            regions=req.regions,
            bookmakers=req.bookmakers,
        )

        best = build_best_market_lines(db_path)
        closing = build_closing_lines(db_path)
        mapped = build_game_id_map(db_path)
        fact_rows = build_fact_game_results_best_market(db_path)

        return {
            "ok": True,
            "odds_snapshot": snap,
            "best_market_rows": best,
            "closing_rows": closing,
            "mapped_rows": mapped,
            "fact_rows": fact_rows,
        }
    except Exception as e:
        print("ODDS REFRESH ERROR:", repr(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))