from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


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
    dates: List[str]  # ["YYYY-MM-DD", ...] (Chicago local day)
    league: str = "nba"
    db: Optional[str] = None


class OddsRefreshRequest(BaseModel):
    sport: str = "basketball_nba"
    regions: str = "us"
    bookmakers: Optional[str] = None
    db: Optional[str] = None