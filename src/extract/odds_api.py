from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import requests

ODDS_API_HOST = "https://api.the-odds-api.com"


def fetch_odds_moneyline(
    sport_key: str,
    regions: str = "us",
    odds_format: str = "american",
    date_format: str = "iso",
    bookmakers: str | None = None,
) -> Tuple[requests.Response, List[Dict[str, Any]]]:
    """Pull upcoming/live odds for a sport, moneyline only (markets=h2h)."""
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        raise RuntimeError("ODDS_API_KEY is not set. Put it in your environment or a .env file.")

    url = f"{ODDS_API_HOST}/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": "h2h",
        "oddsFormat": odds_format,
        "dateFormat": date_format,
    }
    if bookmakers:
        params["bookmakers"] = bookmakers

    r = requests.get(url, params=params, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Odds API error {r.status_code}: {r.text}")

    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected response type: {type(data)}")

    return r, data


def print_quota_headers(r: requests.Response) -> None:
    remaining = r.headers.get("x-requests-remaining")
    used = r.headers.get("x-requests-used")
    last = r.headers.get("x-requests-last")
    print(f"Quota headers -> remaining={remaining} used={used} last_cost={last}")
