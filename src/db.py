from __future__ import annotations

import os
import sqlite3
from typing import Any, Protocol, runtime_checkable, Optional
from urllib.parse import urlparse, unquote

try:
    import psycopg  # type: ignore
except Exception:  # pragma: no cover
    psycopg = None  # allows sqlite-only installs


DDL = """
-- One row per (snapshot, game, sportsbook, market, outcome)
CREATE TABLE IF NOT EXISTS raw_moneyline_odds (
  snapshot_ts TEXT NOT NULL,
  sport_key TEXT NOT NULL,
  event_id TEXT NOT NULL,
  commence_time TEXT,
  home_team TEXT,
  away_team TEXT,

  bookmaker_key TEXT NOT NULL,
  bookmaker_title TEXT,
  bookmaker_last_update TEXT,

  market_key TEXT NOT NULL,
  outcome_name TEXT NOT NULL,
  outcome_price_american INTEGER,

  PRIMARY KEY (snapshot_ts, event_id, bookmaker_key, market_key, outcome_name)
);

-- One row per (game, sportsbook): latest snapshot before game start
CREATE TABLE IF NOT EXISTS fact_closing_moneyline_odds (
  event_id TEXT NOT NULL,
  bookmaker_key TEXT NOT NULL,

  snapshot_ts TEXT NOT NULL,
  commence_time TEXT,
  home_team TEXT,
  away_team TEXT,

  home_price_american INTEGER,
  away_price_american INTEGER,

  PRIMARY KEY (event_id, bookmaker_key)
);

-- One row per game: best available price across all books
CREATE TABLE IF NOT EXISTS fact_best_market_moneyline_odds (
  event_id TEXT NOT NULL,

  commence_time TEXT,
  home_team TEXT,
  away_team TEXT,

  best_home_price_american INTEGER,
  best_home_bookmaker_key TEXT,

  best_away_price_american INTEGER,
  best_away_bookmaker_key TEXT,

  PRIMARY KEY (event_id)
);

-- ESPN scoreboard results (one row per event per date)
CREATE TABLE IF NOT EXISTS raw_espn_game_results (
  scoreboard_date TEXT NOT NULL,        -- YYYYMMDD requested
  espn_event_id   TEXT NOT NULL,
  league          TEXT NOT NULL,        -- e.g. "nba"
  pulled_ts       TEXT NOT NULL,        -- when we pulled it (UTC ISO)

  start_time      TEXT,                -- ESPN event date (ISO)
  status          TEXT,                -- e.g. "Final", "In Progress"
  completed       INTEGER,             -- 1/0

  home_team       TEXT,
  away_team       TEXT,
  home_score      INTEGER,
  away_score      INTEGER,

  PRIMARY KEY (scoreboard_date, espn_event_id)
);

-- Maps Odds API event_id to ESPN event id
CREATE TABLE IF NOT EXISTS game_id_map (
  odds_event_id TEXT PRIMARY KEY,
  espn_event_id TEXT NOT NULL,
  match_method  TEXT,
  matched_ts    TEXT
);

-- Joined fact: best-market odds + final results
CREATE TABLE IF NOT EXISTS fact_game_results_best_market (
  odds_event_id TEXT PRIMARY KEY,
  espn_event_id TEXT NOT NULL,

  commence_time TEXT,
  home_team TEXT,
  away_team TEXT,

  best_home_price_american INTEGER,
  best_away_price_american INTEGER,

  home_score INTEGER,
  away_score INTEGER,

  winner TEXT,           -- "home" or "away"
  favorite_side TEXT,    -- which side had lower (more negative) price
  underdog_side TEXT     -- opposite of favorite
);

-- Calibration summary by implied-probability bucket (favorite side)
CREATE TABLE IF NOT EXISTS fact_calibration_favorite (
  bucket_label TEXT PRIMARY KEY,      -- e.g. "0.50-0.55"
  bucket_min REAL NOT NULL,
  bucket_max REAL NOT NULL,

  n_games INTEGER NOT NULL,
  favorite_win_rate REAL NOT NULL,    -- actual
  avg_implied_prob REAL NOT NULL,     -- expected
  diff_actual_minus_implied REAL NOT NULL  -- calibration error
);

-- Sportsbook vig / margin summary from closing lines
CREATE TABLE IF NOT EXISTS fact_book_margin_summary (
  bookmaker_key TEXT PRIMARY KEY,
  n_games INTEGER NOT NULL,
  avg_overround REAL NOT NULL,
  median_overround REAL NOT NULL,
  min_overround REAL NOT NULL,
  max_overround REAL NOT NULL
);

-- How often each book provides the best available price (best-market frequency)
CREATE TABLE IF NOT EXISTS fact_best_market_frequency (
  bookmaker_key TEXT PRIMARY KEY,
  best_home_count INTEGER NOT NULL,
  best_away_count INTEGER NOT NULL,
  best_total_count INTEGER NOT NULL,
  best_share REAL NOT NULL
);

-- Per-game equity curve for each strategy (for cumulative profit charting)
CREATE TABLE IF NOT EXISTS fact_strategy_equity_curve (
  strategy TEXT NOT NULL,            -- favorite/underdog/home/away
  game_index INTEGER NOT NULL,       -- 1..N in time order

  odds_event_id TEXT NOT NULL,
  espn_event_id TEXT NOT NULL,
  commence_time TEXT,

  stake REAL NOT NULL,
  odds_american INTEGER NOT NULL,
  picked_side TEXT NOT NULL,         -- home/away
  winner TEXT NOT NULL,              -- home/away

  bet_profit REAL NOT NULL,          -- profit for that bet (can be negative)
  cum_profit REAL NOT NULL,          -- cumulative profit
  cum_roi REAL NOT NULL,             -- cum_profit / (game_index*stake)

  PRIMARY KEY (strategy, odds_event_id)
);

-- Dashboard KPI rollup (key/value style for flexibility)
CREATE TABLE IF NOT EXISTS fact_dashboard_kpis (
  kpi_name TEXT PRIMARY KEY,
  kpi_value TEXT NOT NULL
);
"""


def _is_postgres_target(target: str) -> bool:
    t = (target or "").strip().lower()
    return t.startswith("postgres://") or t.startswith("postgresql://")


def _sqlite_path_from_target(target: str) -> str:
    """
    Convert SQLite targets into a filesystem path usable by sqlite3.connect().

    Supports:
      - "sqlite:///data/demo_odds.sqlite"  (URL form)
      - "data/demo_odds.sqlite"           (path form)
      - "/abs/path/demo_odds.sqlite"      (absolute path)
    """
    t = (target or "").strip()

    if t.lower().startswith("sqlite:"):
        u = urlparse(t)
        path = unquote(u.path or "")

        # Common .env style: sqlite:///data/demo_odds.sqlite
        # urlparse makes path="/data/demo_odds.sqlite" — we want repo-relative "data/demo_odds.sqlite"
        if path.startswith("/"):
            path = path[1:]

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        t = os.path.join(repo_root, path)

    # If still relative, resolve relative to repo root
    if not os.path.isabs(t):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        t = os.path.join(repo_root, t)

    # Ensure parent directory exists
    parent = os.path.dirname(os.path.abspath(t))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    return t


def connect(db_path_or_url: Optional[str] = None):
    """
    Connect to SQLite (path) or Postgres (URL).

    - If db_path_or_url is None, uses env DATABASE_URL if set, else falls back to data/demo_odds.sqlite.
    - SQLite: pass a filesystem path like "data/demo_odds.sqlite"
    - Postgres: pass a URL like "postgresql://user:pass@localhost:5432/dbname"
    """
    target = db_path_or_url or os.getenv("DATABASE_URL") or "data/demo_odds.sqlite"

    if _is_postgres_target(target):
        if psycopg is None:
            raise RuntimeError(
                "Postgres DATABASE_URL provided but psycopg is not installed. "
                "Add 'psycopg[binary]' to requirements.txt."
            )
        conn = psycopg.connect(target)  # type: ignore
        # Important: most of your ETL does inserts/updates; autocommit off is fine.
        return conn

    # SQLite path (or sqlite URL)
    sqlite_path = _sqlite_path_from_target(target)
    conn = sqlite3.connect(sqlite_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def ensure_schema(conn) -> None:
    """
    Create required tables if they don't exist (SQLite or Postgres).
    """
    module = conn.__class__.__module__
    is_sqlite = module.startswith("sqlite3")
    is_postgres = module.startswith("psycopg")

    if is_sqlite:
        conn.executescript(DDL)
        conn.commit()
        return

    if is_postgres:
        # psycopg doesn't have executescript; run statements one-by-one.
        # This simplistic split works because your DDL statements end in semicolons and don't contain functions.
        statements = [s.strip() for s in DDL.split(";") if s.strip()]
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
        return

    raise TypeError(f"Unsupported connection type: {type(conn)}")
