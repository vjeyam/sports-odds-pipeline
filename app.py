from __future__ import annotations

import os
import sqlite3
import hmac
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv, find_dotenv

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.pipelines.run_full_pipeline import run_transforms
from src.pipelines.run_odds_snapshot import run_odds_snapshot
from src.pipelines.run_espn_results_pull import run_espn_results_pull

load_dotenv(find_dotenv(), override=True)


# Page config
st.set_page_config(
    page_title="Sports Market Efficiency & Pricing Analysis",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Sports Market Efficiency & Pricing Analysis")
st.caption("Equity • Calibration • Vig/Overround • Best-market frequency • KPIs")

# Config
DEFAULT_DB_PATH = "odds.sqlite"
ADMIN_KEY_ENV = "ADMIN_KEY"


@dataclass(frozen=True)
class Filters:
    strategy: str
    start_date: Optional[pd.Timestamp]
    end_date: Optional[pd.Timestamp]


# Admin controls/config
def is_admin() -> bool:
    expected = os.getenv(ADMIN_KEY_ENV, "")
    entered = st.session_state.get("admin_key_input", "")

    expected = expected.strip()
    entered = str(entered).strip()

    if not expected:
        return False

    return hmac.compare_digest(entered, expected)


def should_cancel() -> bool:
    return bool(st.session_state.get("cancel_pipeline", False))


def admin_controls() -> None:
    with st.sidebar.expander("Admin", expanded=False):
        st.text_input("Admin key", type="password", key="admin_key_input")

        if is_admin():
            st.success("Admin mode enabled")

            st.toggle(
                "Lock user updates",
                key="lock_user_updates",
                value=st.session_state.get("lock_user_updates", False),
                help="When enabled, non-admin users cannot run updates.",
            )

            st.button(
                "Cancel current run",
                key="cancel_pipeline",
                help="Stops the pipeline between stages (soft cancel).",
            )
        else:
            st.caption("Enter admin key to unlock admin controls.")


def run_full_update(db_path: str, stake: float, cal_step: float) -> dict:
    """
    One-click ETL: Pull odds -> Pull ESPN results -> Transforms.
    Supports soft cancel between stages.
    """
    st.session_state["cancel_pipeline"] = False
    summary: dict = {"status": "started", "stages": []}

    if should_cancel():
        summary["status"] = "cancelled_before_odds"
        return summary
    out1 = run_odds_snapshot(db_path=db_path)
    summary["stages"].append({"pull_odds": out1})

    if should_cancel():
        summary["status"] = "cancelled_before_results"
        return summary
    out2 = run_espn_results_pull(db_path=db_path)
    summary["stages"].append({"pull_results": out2})

    if should_cancel():
        summary["status"] = "cancelled_before_transforms"
        return summary
    out3 = run_transforms(db_path, stake=float(stake), calibration_step=float(cal_step))
    summary["stages"].append({"transforms": getattr(out3, "__dict__", out3)})

    summary["status"] = "finished"
    return summary


# SQLite helpers
@st.cache_resource
def get_conn(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path, check_same_thread=False)


@st.cache_data(show_spinner=False)
def table_exists(db_path: str, name: str) -> bool:
    conn = get_conn(db_path)
    q = """
    SELECT 1
    FROM sqlite_master
    WHERE type IN ('table','view') AND name = ?
    LIMIT 1;
    """
    cur = conn.execute(q, (name,))
    return cur.fetchone() is not None


def wal_checkpoint(db_path: str) -> None:
    try:
        conn = get_conn(db_path)
        conn.execute("PRAGMA wal_checkpoint(FULL);")
        conn.commit()
    except Exception:
        pass


@st.cache_data(show_spinner=False)
def load_table_counts(db_path: str) -> pd.DataFrame:
    conn = get_conn(db_path)
    tables = [
        "raw_odds_moneyline",
        "raw_espn_game_results",
        "fact_closing_moneyline_odds",
        "fact_best_market_moneyline_odds",
        "game_id_map",
        "fact_game_results_best_market",
        "fact_strategy_equity_curve",
        "fact_calibration_favorite",
        "fact_book_margin_summary",
        "fact_best_market_frequency",
        "fact_dashboard_kpis",
    ]
    rows = []
    for t in tables:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            rows.append((t, int(n)))
        except Exception:
            rows.append((t, None))
    return pd.DataFrame(rows, columns=["table", "rows"])


def diff_counts(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    b = before.set_index("table")["rows"]
    a = after.set_index("table")["rows"]
    out = pd.concat([b, a], axis=1)
    out.columns = ["rows_before", "rows_after"]
    out["delta"] = out["rows_after"] - out["rows_before"]
    return out.reset_index()


# Loads
@st.cache_data(show_spinner=False)
def load_available_dimensions(db_path: str) -> dict:
    conn = get_conn(db_path)
    q_strat = """
    SELECT DISTINCT strategy
    FROM fact_strategy_equity_curve
    ORDER BY strategy;
    """
    q_dates = """
    SELECT MIN(commence_time) AS min_d, MAX(commence_time) AS max_d
    FROM fact_strategy_equity_curve;
    """
    strategies = pd.read_sql(q_strat, conn)["strategy"].dropna().tolist()
    d = pd.read_sql(q_dates, conn).iloc[0].to_dict()
    min_d = pd.to_datetime(d["min_d"]) if d["min_d"] is not None else None
    max_d = pd.to_datetime(d["max_d"]) if d["max_d"] is not None else None
    return {"strategies": strategies, "min_date": min_d, "max_date": max_d}


@st.cache_data(show_spinner=True)
def load_equity_curve(db_path: str, f: Filters) -> pd.DataFrame:
    conn = get_conn(db_path)
    sql = """
    SELECT
        commence_time AS event_date,
        game_index,
        stake,
        odds_american,
        picked_side,
        winner,
        bet_profit AS profit,
        cum_profit,
        cum_roi,
        odds_event_id,
        espn_event_id
    FROM fact_strategy_equity_curve
    WHERE strategy = :strategy
      AND (:start_date IS NULL OR date(commence_time) >= date(:start_date))
      AND (:end_date IS NULL OR date(commence_time) <= date(:end_date))
    ORDER BY game_index;
    """
    params = {
        "strategy": f.strategy,
        "start_date": None if f.start_date is None else str(f.start_date.date()),
        "end_date": None if f.end_date is None else str(f.end_date.date()),
    }
    df = pd.read_sql(sql, conn, params=params)
    if df.empty:
        return df

    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    for c in ["stake", "profit", "cum_profit", "cum_roi"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["game_index"] = pd.to_numeric(df["game_index"], errors="coerce").astype("Int64")
    return df.dropna(subset=["event_date"]).copy()


@st.cache_data(show_spinner=False)
def load_calibration(db_path: str) -> pd.DataFrame:
    conn = get_conn(db_path)
    sql = """
    SELECT
        bucket_label,
        bucket_min,
        bucket_max,
        n_games,
        favorite_win_rate,
        avg_implied_prob,
        diff_actual_minus_implied
    FROM fact_calibration_favorite
    ORDER BY bucket_min;
    """
    return pd.read_sql(sql, conn)


@st.cache_data(show_spinner=False)
def load_book_margin_summary(db_path: str) -> pd.DataFrame:
    conn = get_conn(db_path)
    sql = """
    SELECT
        bookmaker_key,
        n_games,
        avg_overround,
        median_overround,
        min_overround,
        max_overround
    FROM fact_book_margin_summary
    ORDER BY avg_overround ASC;
    """
    return pd.read_sql(sql, conn)


@st.cache_data(show_spinner=False)
def load_best_market_frequency(db_path: str) -> pd.DataFrame:
    conn = get_conn(db_path)
    sql = """
    SELECT
        bookmaker_key,
        best_home_count,
        best_away_count,
        best_total_count,
        best_share
    FROM fact_best_market_frequency
    ORDER BY best_share DESC;
    """
    return pd.read_sql(sql, conn)


@st.cache_data(show_spinner=False)
def load_kpis(db_path: str) -> pd.DataFrame:
    conn = get_conn(db_path)
    sql = "SELECT kpi_name, kpi_value FROM fact_dashboard_kpis ORDER BY kpi_name;"
    return pd.read_sql(sql, conn)


def kpi_map_from_table(kpis_tbl: pd.DataFrame) -> dict:
    if kpis_tbl is None or kpis_tbl.empty:
        return {}
    if not {"kpi_name", "kpi_value"} <= set(kpis_tbl.columns):
        return {}
    return dict(zip(kpis_tbl["kpi_name"], kpis_tbl["kpi_value"]))


# KPI computation
def compute_kpis_from_equity(eq: pd.DataFrame) -> dict:
    if eq.empty:
        return {}
    total_profit = float(eq["profit"].sum())
    total_staked = float(eq["stake"].sum()) if "stake" in eq.columns else np.nan
    n = int(len(eq))
    wins = int((eq["profit"] > 0).sum())
    win_rate = wins / n if n else np.nan
    roi = (total_profit / total_staked) if total_staked and total_staked != 0 else np.nan

    equity = eq["profit"].cumsum()
    peak = equity.cummax()
    dd = equity - peak
    max_dd = float(dd.min()) if len(dd) else 0.0

    gross_win = float(eq.loc[eq["profit"] > 0, "profit"].sum())
    gross_loss = float(-eq.loc[eq["profit"] < 0, "profit"].sum())
    pf = (gross_win / gross_loss) if gross_loss != 0 else np.inf

    return {
        "Bets": n,
        "Profit": total_profit,
        "Staked": total_staked,
        "ROI": roi,
        "Win Rate": win_rate,
        "Max Drawdown": max_dd,
        "Profit Factor": pf,
    }


def render_kpi_cards(kpis: dict) -> None:
    c = st.columns(7)
    c[0].metric("Bets", f"{kpis.get('Bets', 0):,}")
    c[1].metric("Profit", f"{kpis.get('Profit', 0):,.2f}")
    c[2].metric("Staked", f"{kpis.get('Staked', 0):,.2f}")
    roi = kpis.get("ROI", np.nan)
    c[3].metric("ROI", f"{roi * 100:.2f}%" if np.isfinite(roi) else "—")
    wr = kpis.get("Win Rate", np.nan)
    c[4].metric("Win Rate", f"{wr * 100:.1f}%" if np.isfinite(wr) else "—")
    c[5].metric("Max DD", f"{kpis.get('Max Drawdown', 0):,.2f}")
    pf = kpis.get("Profit Factor", np.inf)
    c[6].metric("Profit Factor", f"{pf:.2f}" if np.isfinite(pf) else "∞")


# Sidebar + Mode selection
st.session_state.setdefault("last_pipeline_diff", None)
st.session_state.setdefault("last_pipeline_error", None)
st.session_state.setdefault("last_update_summary", None)
st.session_state.setdefault("lock_user_updates", False)
st.session_state.setdefault("cancel_pipeline", False)

admin_controls()
admin_mode = is_admin()

if admin_mode and not os.getenv(ADMIN_KEY_ENV):
    st.sidebar.warning("ADMIN_KEY is not set (check your .env).")

# DB path: hidden for users, visible for admin
db_path = DEFAULT_DB_PATH
if admin_mode:
    st.sidebar.markdown("---")
    db_path = st.sidebar.text_input("SQLite DB Path", value=DEFAULT_DB_PATH)

if not os.path.exists(db_path):
    st.error(f"Database not found at: {db_path}")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.markdown("### Update")

stake = st.sidebar.number_input("Stake (strategy sim)", value=1.0, step=0.25)
cal_step = st.sidebar.selectbox("Calibration step", options=[0.02, 0.05, 0.10], index=1)
auto_scale_cal = st.sidebar.checkbox("Auto-scale calibration axes", value=False)

updates_locked = bool(st.session_state.get("lock_user_updates", False))
can_run = admin_mode or not updates_locked

if not can_run:
    st.sidebar.button("Update Odds (Run ETL)", disabled=True, use_container_width=True)
    st.sidebar.warning("Updates are disabled by admin.")
else:
    if st.sidebar.button("Update Odds (Run ETL)", use_container_width=True):
        st.session_state["last_pipeline_error"] = None
        before = load_table_counts(db_path)
        try:
            with st.spinner("Running ETL: odds → results → transforms..."):
                st.session_state["last_update_summary"] = run_full_update(
                    db_path=db_path, stake=float(stake), cal_step=float(cal_step)
                )
            wal_checkpoint(db_path)
        except Exception as e:
            st.session_state["last_pipeline_error"] = str(e)

        st.cache_data.clear()
        st.cache_resource.clear()
        after = load_table_counts(db_path)
        st.session_state["last_pipeline_diff"] = diff_counts(before, after)
        st.rerun()

# raw previews only for admin
show_raw = False
if admin_mode:
    st.sidebar.markdown("---")
    show_raw = st.sidebar.checkbox("Show raw tables (previews)", value=False)

# Required table for the dashboard to function
if not table_exists(db_path, "fact_strategy_equity_curve"):
    st.warning("Missing required table: fact_strategy_equity_curve. Run Update Odds (Run ETL).")
    if admin_mode:
        st.stop()
    else:
        st.stop()


# Admin-only pipeline debug sections (HIDDEN from users)
if admin_mode:
    if st.session_state.get("last_pipeline_error"):
        st.error(f"Last pipeline action error:\n\n{st.session_state['last_pipeline_error']}")

    if st.session_state.get("last_pipeline_diff") is not None:
        with st.expander("Last pipeline run: table row deltas"):
            st.dataframe(st.session_state["last_pipeline_diff"], use_container_width=True)

    kpis_tbl = load_kpis(db_path) if table_exists(db_path, "fact_dashboard_kpis") else pd.DataFrame()
    kmap = kpi_map_from_table(kpis_tbl)

    with st.expander("Pipeline status (tables + row counts)"):
        built_ts = kmap.get("kpis_built_ts_utc") or kmap.get("built_ts_utc") or kmap.get("kpi_built_ts_utc")
        if built_ts:
            st.write(f"Last KPI build (UTC): **{built_ts}**")
        counts = load_table_counts(db_path)
        st.dataframe(counts, use_container_width=True)

        if table_exists(db_path, "fact_calibration_favorite"):
            buckets = load_calibration(db_path)[["bucket_label", "bucket_min", "bucket_max", "n_games"]]
            st.write("Calibration buckets (from fact_calibration_favorite):")
            st.dataframe(buckets, use_container_width=True)


# Dimensions + filters
dims = load_available_dimensions(db_path)
strategy = st.sidebar.selectbox("Strategy", options=dims["strategies"] or ["favorite"])

min_d, max_d = dims["min_date"], dims["max_date"]
c1, c2 = st.sidebar.columns(2)
start_date = c1.date_input("Start", value=min_d.date() if min_d is not None else None)
end_date = c2.date_input("End", value=max_d.date() if max_d is not None else None)

filt = Filters(
    strategy=strategy,
    start_date=pd.to_datetime(start_date) if start_date else None,
    end_date=pd.to_datetime(end_date) if end_date else None,
)


# Load fact tables
equity = load_equity_curve(db_path, filt)
if equity.empty:
    st.warning("No equity rows match the current filters. Try widening your date range.")
    st.stop()

cal = load_calibration(db_path) if table_exists(db_path, "fact_calibration_favorite") else pd.DataFrame()
book_margin = load_book_margin_summary(db_path) if table_exists(db_path, "fact_book_margin_summary") else pd.DataFrame()
best_mkt = load_best_market_frequency(db_path) if table_exists(db_path, "fact_best_market_frequency") else pd.DataFrame()


# KPIs (filtered)
kpis = compute_kpis_from_equity(equity)
render_kpi_cards(kpis)

st.markdown("---")


# Layout
left, right = st.columns([1.35, 1.0], gap="large")

with left:
    st.subheader("Cumulative Profit (Equity Curve)")
    st.caption(
        f"rows={len(equity)} | "
        f"cum_profit=[{equity['cum_profit'].min():.3f}, {equity['cum_profit'].max():.3f}] | "
        f"profit=[{equity['profit'].min():.3f}, {equity['profit'].max():.3f}]"
    )
    fig_eq = px.line(equity, x="event_date", y="cum_profit")
    fig_eq.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_eq, use_container_width=True)

    st.subheader("Calibration (Favorite: actual vs implied)")
    if cal.empty:
        st.info("Calibration table not found (fact_calibration_favorite).")
    else:
        st.caption(
            f"buckets={len(cal)} | "
            f"avg_implied_prob=[{cal['avg_implied_prob'].min():.3f}, {cal['avg_implied_prob'].max():.3f}] | "
            f"favorite_win_rate=[{cal['favorite_win_rate'].min():.3f}, {cal['favorite_win_rate'].max():.3f}]"
        )
        fig_cal = go.Figure()
        fig_cal.add_trace(
            go.Scatter(
                x=cal["avg_implied_prob"],
                y=cal["favorite_win_rate"],
                mode="markers+lines",
                name="Favorite",
                customdata=np.stack([cal["n_games"], cal["bucket_label"]], axis=1),
                hovertemplate="bucket=%{customdata[1]}<br>n=%{customdata[0]}<br>implied=%{x:.3f}<br>actual=%{y:.3f}<extra></extra>",
            )
        )
        fig_cal.add_trace(
            go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect", line=dict(dash="dash"))
        )
        fig_cal.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
        fig_cal.update_xaxes(title="Avg implied probability")
        fig_cal.update_yaxes(title="Favorite win rate")
        if not auto_scale_cal:
            fig_cal.update_xaxes(range=[0, 1])
            fig_cal.update_yaxes(range=[0, 1])
        st.plotly_chart(fig_cal, use_container_width=True)

with right:
    st.subheader("Vig / Overround by Book (Closing)")
    if book_margin.empty:
        st.info("Book margin table not found (fact_book_margin_summary).")
    else:
        st.caption(
            f"books={len(book_margin)} | "
            f"avg_overround=[{book_margin['avg_overround'].min():.4f}, {book_margin['avg_overround'].max():.4f}]"
        )
        fig_vig = px.bar(
            book_margin.sort_values("avg_overround", ascending=True),
            x="avg_overround",
            y="bookmaker_key",
            orientation="h",
            hover_data=["n_games", "median_overround", "min_overround", "max_overround"],
        )
        fig_vig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
        fig_vig.update_xaxes(title="Average overround")
        fig_vig.update_yaxes(title="")
        st.plotly_chart(fig_vig, use_container_width=True)

    st.subheader("Best-market Frequency")
    if best_mkt.empty:
        st.info("Best-market table not found (fact_best_market_frequency).")
    else:
        st.caption(
            f"books={len(best_mkt)} | "
            f"best_share=[{best_mkt['best_share'].min():.4f}, {best_mkt['best_share'].max():.4f}]"
        )
        fig_bm = px.bar(
            best_mkt.sort_values("best_share", ascending=False),
            x="best_share",
            y="bookmaker_key",
            orientation="h",
            hover_data=["best_total_count", "best_home_count", "best_away_count"],
        )
        fig_bm.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
        fig_bm.update_xaxes(title="Best-market share")
        fig_bm.update_yaxes(title="")
        st.plotly_chart(fig_bm, use_container_width=True)

st.markdown("---")

if show_raw:
    with st.expander("Raw previews"):
        st.write("Equity curve rows", equity.shape)
        st.dataframe(equity, use_container_width=True)

        if not cal.empty:
            st.write("Calibration rows", cal.shape)
            st.dataframe(cal, use_container_width=True)

        if not book_margin.empty:
            st.write("Book margin rows", book_margin.shape)
            st.dataframe(book_margin, use_container_width=True)

        if not best_mkt.empty:
            st.write("Best market rows", best_mkt.shape)
            st.dataframe(best_mkt, use_container_width=True)
