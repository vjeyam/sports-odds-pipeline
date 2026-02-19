from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI

from api.router.analytics import router as analytics_router
from api.router.etl import router as etl_router
from api.router.games import router as games_router
from api.router.health import router as health_router
from api.router.jobs import router as jobs_router
from api.router.strategies import router as strategies_router

load_dotenv()

app = FastAPI(title="Sports Odds ETL API", version="0.1.0")


@app.on_event("startup")
def _startup_env_check() -> None:
    # Keep your env print, but only on startup (not import-time).
    print(
        "ENV CHECK:",
        {
            "ODDS_API_KEY": bool(os.getenv("ODDS_API_KEY")),
            "DATABASE_URL": os.getenv("DATABASE_URL"),
        },
    )


@app.get("/")
def root():
    return {"service": "sports-odds-etl-api", "health": "/health", "docs": "/docs"}


# Routers
app.include_router(health_router)
app.include_router(games_router)
app.include_router(analytics_router)
app.include_router(strategies_router)
app.include_router(etl_router)
app.include_router(jobs_router)