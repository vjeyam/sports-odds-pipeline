from __future__ import annotations

from typing import Any, Dict
import requests

ESPN_HOST = "https://site.api.espn.com"


def fetch_nba_scoreboard(date_yyyymmdd: str) -> Dict[str, Any]:
    """
    ESPN scoreboard endpoint (unofficial):
    /apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD
    """
    url = f"{ESPN_HOST}/apis/site/v2/sports/basketball/nba/scoreboard"
    r = requests.get(url, params={"dates": date_yyyymmdd}, timeout=30)
    r.raise_for_status()
    return r.json()