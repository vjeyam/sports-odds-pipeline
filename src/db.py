import sqlite3

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
"""

def connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection with pragmatic defaults for ETL."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create required tables if they don't exist."""
    conn.executescript(DDL)
    conn.commit()