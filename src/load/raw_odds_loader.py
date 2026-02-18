from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from src.db import connect, ensure_schema


def _is_postgres(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg")


def _ph(conn) -> str:
    return "%s" if _is_postgres(conn) else "?"


def flatten_moneyline(snapshot_ts: str, payload: List[Dict[str, Any]]) -> List[Tuple]:
    """Flatten Odds API v4 response into rows for raw_moneyline_odds."""
    rows: List[Tuple] = []

    for event in payload:
        event_id = event.get("id")
        sport_key = event.get("sport_key")
        commence_time = event.get("commence_time")
        home_team = event.get("home_team")
        away_team = event.get("away_team")

        for bm in event.get("bookmakers", []) or []:
            bm_key = bm.get("key")
            bm_title = bm.get("title")
            bm_last_update = bm.get("last_update")

            for market in bm.get("markets", []) or []:
                market_key = market.get("key")
                if market_key != "h2h":
                    continue

                for outcome in market.get("outcomes", []) or []:
                    outcome_name = outcome.get("name")
                    price = outcome.get("price")
                    if outcome_name is None or price is None:
                        continue

                    rows.append(
                        (
                            snapshot_ts,
                            sport_key,
                            event_id,
                            commence_time,
                            home_team,
                            away_team,
                            bm_key,
                            bm_title,
                            bm_last_update,
                            market_key,
                            outcome_name,
                            int(price),
                        )
                    )
    return rows


def insert_raw_moneyline_rows(db_path: str, rows: Iterable[Tuple]) -> int:
    conn = connect(db_path)
    ensure_schema(conn)

    is_pg = _is_postgres(conn)
    ph = _ph(conn)

    rows_list = list(rows)
    if not rows_list:
        try:
            conn.close()
        except Exception:
            pass
        return 0

    cols = """
      snapshot_ts, sport_key, event_id, commence_time, home_team, away_team,
      bookmaker_key, bookmaker_title, bookmaker_last_update,
      market_key, outcome_name, outcome_price_american
    """.strip()

    placeholders = ", ".join([ph] * 12)

    # Base INSERT that works in both
    sql = f"INSERT INTO raw_moneyline_odds ({cols}) VALUES ({placeholders})"

    # Dedup handling
    if is_pg:
        # Match the PRIMARY KEY defined in your DDL
        sql += " ON CONFLICT (snapshot_ts, event_id, bookmaker_key, market_key, outcome_name) DO NOTHING"
    else:
        # SQLite equivalent
        sql = f"INSERT OR IGNORE INTO raw_moneyline_odds ({cols}) VALUES ({placeholders})"

    inserted_or_ignored = 0

    if is_pg:
        # psycopg requires using a cursor object
        with conn.cursor() as cur:
            cur.executemany(sql, rows_list)
            # rowcount is "rows inserted" (duplicates ignored => not counted)
            inserted_or_ignored = cur.rowcount if cur.rowcount is not None else 0
        conn.commit()
        conn.close()
        return inserted_or_ignored

    # sqlite3 can execute directly on the connection too, but cursor is fine
    cur = conn.cursor()
    cur.executemany(sql, rows_list)
    conn.commit()
    inserted_or_ignored = cur.rowcount
    conn.close()
    return inserted_or_ignored
