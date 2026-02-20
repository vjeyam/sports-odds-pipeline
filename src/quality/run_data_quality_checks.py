from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from src.db import connect, ensure_schema


def _is_postgres_conn(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg")


def _first_col(row: Optional[Sequence[Any]], default: Any = 0) -> Any:
    return row[0] if row is not None and len(row) > 0 else default


def _parse_iso(dt: Optional[str]) -> Optional[datetime]:
    if not dt:
        return None
    s = dt.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def run_data_quality_checks(db: str, *, missing_results_hours: int = 12) -> dict[str, Any]:
    """
    QC checks aligned to your schema:

    - % mapped to ESPN:
        fact_best_market_moneyline_odds.event_id vs game_id_map.odds_event_id
    - games with odds but no results after X hours:
        fact_best_market_moneyline_odds LEFT JOIN fact_game_results_best_market
    - duplicate ESPN mappings:
        game_id_map has multiple odds_event_id pointing to same espn_event_id
    """
    out: dict[str, Any] = {}

    conn = connect(db)
    ensure_schema(conn)
    is_pg = _is_postgres_conn(conn)

    try:
        cur = conn.cursor() if is_pg else conn

        # -------------------------
        # QC1) % mapped to ESPN
        # -------------------------
        total_odds_events = int(
            _first_col(
                cur.execute("SELECT COUNT(*) FROM fact_best_market_moneyline_odds").fetchone(),
                0,
            )
        )

        mapped_odds_events = int(
            _first_col(
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM fact_best_market_moneyline_odds o
                    JOIN game_id_map m
                      ON m.odds_event_id = o.event_id
                    """
                ).fetchone(),
                0,
            )
        )

        out["odds_events_total"] = total_odds_events
        out["odds_events_mapped_to_espn"] = mapped_odds_events
        out["mapped_pct"] = (mapped_odds_events / total_odds_events) if total_odds_events else None

        # -------------------------
        # QC2) odds but no results after X hours
        # -------------------------
        cutoff = datetime.now(timezone.utc) - timedelta(hours=missing_results_hours)

        rows = cur.execute(
            """
            SELECT
              o.event_id,
              o.commence_time,
              CASE WHEN r.odds_event_id IS NULL THEN 1 ELSE 0 END AS missing_results
            FROM fact_best_market_moneyline_odds o
            LEFT JOIN fact_game_results_best_market r
              ON r.odds_event_id = o.event_id
            """
        ).fetchall()

        missing_total = 0
        missing_after_cutoff = 0

        for event_id, commence_time, missing_flag in rows:
            if int(missing_flag) != 1:
                continue
            missing_total += 1

            ct = _parse_iso(commence_time)
            if ct and ct.tzinfo is None:
                ct = ct.replace(tzinfo=timezone.utc)

            if ct and ct <= cutoff:
                missing_after_cutoff += 1

        out["odds_games_missing_results_total"] = int(missing_total)
        out[f"odds_games_missing_results_after_{missing_results_hours}h"] = int(missing_after_cutoff)

        # -------------------------
        # QC3) duplicate ESPN mappings
        # -------------------------
        dup_map = int(
            _first_col(
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM (
                      SELECT espn_event_id
                      FROM game_id_map
                      GROUP BY espn_event_id
                      HAVING COUNT(*) > 1
                    ) x
                    """
                ).fetchone(),
                0,
            )
        )
        out["duplicate_espn_event_id_in_game_id_map"] = int(dup_map)

        # -------------------------
        # Thresholds / status
        # -------------------------
        status = "PASS"
        reasons: list[str] = []

        mapped_pct = out.get("mapped_pct")
        if mapped_pct is not None and mapped_pct < 0.90:
            status = "FAIL"
            reasons.append("mapped_pct<0.90")

        if out["duplicate_espn_event_id_in_game_id_map"] > 0:
            status = "FAIL"
            reasons.append("duplicate_espn_event_id_in_game_id_map>0")

        # Treat this as fail only if it's meaningfully high
        if out[f"odds_games_missing_results_after_{missing_results_hours}h"] > 5:
            status = "FAIL"
            reasons.append(f"missing_results_after_{missing_results_hours}h>5")

        out["qc_status"] = status
        out["qc_reasons"] = reasons
        return out

    finally:
        try:
            conn.close()
        except Exception:
            pass


def main() -> int:
    import argparse
    import os

    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.getenv("DATABASE_URL") or "odds.sqlite")
    ap.add_argument("--missing-results-hours", type=int, default=12)
    ap.add_argument("--fail", action="store_true")
    args = ap.parse_args()

    qc = run_data_quality_checks(args.db, missing_results_hours=args.missing_results_hours)
    for k, v in qc.items():
        print(f"{k}: {v}")

    if args.fail and qc.get("qc_status") != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())