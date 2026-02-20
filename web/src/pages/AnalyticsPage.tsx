import { useEffect, useMemo, useState } from "react";
import {
  getAnalyticsDaily,
  getAnalyticsSummary,
  getStrategiesSummary,
  getStrategyEquity,
  getStrategyRoiBuckets,
  type AnalyticsDailyRow,
  type AnalyticsSummary,
  type RoiBucketRow,
  type StrategyEquityPoint,
  type StrategyName,
  type StrategySummaryRow,
} from "../lib/api";
import { ErrorBox } from "../components/ErrorBox";
import EquityCurveChart from "../components/EquityCurveChart";
import RoiBucketsChart from "../components/RoiBucketsChart";
import { th, td } from "../styles/ui";

import "../styles/analytics.css";

function todayISO(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function isoDaysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function pct(x: number | null) {
  if (x == null) return "—";
  return `${(x * 100).toFixed(1)}%`;
}

function money(x: number | null) {
  if (x == null) return "—";
  return x >= 0 ? `+${x.toFixed(2)}` : x.toFixed(2);
}

function stratLabel(s: StrategyName) {
  if (s === "favorite") return "Favorite";
  if (s === "underdog") return "Underdog";
  if (s === "home") return "Home";
  return "Away";
}

type ChartsLayout = "scroll" | "two-up";

export default function AnalyticsPage() {
  const [start, setStart] = useState(() => isoDaysAgo(7));
  const [end, setEnd] = useState(() => todayISO());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [daily, setDaily] = useState<AnalyticsDailyRow[]>([]);

  // Strategy perf
  const [strategyRows, setStrategyRows] = useState<StrategySummaryRow[]>([]);
  const [strategy, setStrategy] = useState<StrategyName>("favorite");
  const [equity, setEquity] = useState<StrategyEquityPoint[]>([]);
  const [buckets, setBuckets] = useState<RoiBucketRow[]>([]);
  const [nBetsInBuckets, setNBetsInBuckets] = useState<number>(0);

  // view toggle for charts
  const [chartsLayout, setChartsLayout] = useState<ChartsLayout>("scroll");

  const rangeLabel = useMemo(() => `Range: ${start} → ${end}`, [start, end]);

  async function loadAll() {
    setLoading(true);
    setError(null);

    try {
      const [s, d, stratSummary, stratEquity, stratBuckets] = await Promise.all([
        getAnalyticsSummary(start, end),
        getAnalyticsDaily(start, end),
        getStrategiesSummary(start, end),
        getStrategyEquity(strategy, start, end),
        getStrategyRoiBuckets(strategy, start, end),
      ]);

      setSummary(s);
      setDaily(d.daily);
      setStrategyRows(stratSummary.strategies);
      setEquity(stratEquity.equity);
      setBuckets(stratBuckets.buckets);
      setNBetsInBuckets(stratBuckets.n_bets_in_range);
    } catch (e) {
      setSummary(null);
      setDaily([]);
      setStrategyRows([]);
      setEquity([]);
      setBuckets([]);
      setNBetsInBuckets(0);
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function loadStrategyOnly(next: StrategyName) {
    setStrategy(next);
    setError(null);

    try {
      const [eq, rb] = await Promise.all([getStrategyEquity(next, start, end), getStrategyRoiBuckets(next, start, end)]);
      setEquity(eq.equity);
      setBuckets(rb.buckets);
      setNBetsInBuckets(rb.n_bets_in_range);
    } catch (e) {
      setEquity([]);
      setBuckets([]);
      setNBetsInBuckets(0);
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }

  function quickRange(days: number) {
    setStart(isoDaysAgo(days));
    setEnd(todayISO());
  }

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [start, end]);

  const chartsClass = chartsLayout === "two-up" ? "chartsTwoUp" : "chartsScroll";

  return (
    <div className="analyticsPage">
      {/* Header */}
      <div className="analyticsHeader">
        <div className="analyticsTitle">Analytics</div>
        <div className="analyticsSubtitle">
          This page summarizes outcomes and simple strategy performance for the selected date range. ROI assumes a <b>$1 stake</b> per game.
        </div>
      </div>

      {/* Controls */}
      <div className="card">
        <div className="controlsRow">
          <label className="field">
            <span className="fieldLabel">Start</span>
            <input className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </label>

          <label className="field">
            <span className="fieldLabel">End</span>
            <input className="input" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>

          <button className="btn" onClick={loadAll} disabled={loading}>
            {loading ? "Loading..." : "Reload Analytics"}
          </button>

          <button className="btn btnGhost" onClick={() => quickRange(7)} disabled={loading}>
            Last 7d
          </button>
          <button className="btn btnGhost" onClick={() => quickRange(14)} disabled={loading}>
            Last 14d
          </button>
          <button className="btn btnGhost" onClick={() => quickRange(30)} disabled={loading}>
            Last 30d
          </button>

          <div className="toolbarRowRight">
            <span className="pill">{rangeLabel}</span>

            <div className="segmented" title="Change how charts are laid out">
              <button
                className={`segmentBtn ${chartsLayout === "scroll" ? "segmentBtnActive" : ""}`}
                onClick={() => setChartsLayout("scroll")}
                type="button"
              >
                Scroll
              </button>
              <button
                className={`segmentBtn ${chartsLayout === "two-up" ? "segmentBtnActive" : ""}`}
                onClick={() => setChartsLayout("two-up")}
                type="button"
              >
                2-up charts
              </button>
            </div>
          </div>
        </div>
      </div>

      <ErrorBox error={error} />

      {/* KPI cards */}
      {summary && (
        <>
          <div className="kpiGrid">
            <div className="kpiCard">
              <div className="kpiLabel">Games with odds</div>
              <div className="kpiValue">{summary.n_games_with_odds}</div>
            </div>

            <div className="kpiCard">
              <div className="kpiLabel">Decided games</div>
              <div className="kpiValue">{summary.n_decided_games}</div>
            </div>

            <div className="kpiCard">
              <div className="kpiLabel">Favorite win rate</div>
              <div className="kpiValue">{pct(summary.favorite_win_rate)}</div>
            </div>

            <div className="kpiCard">
              <div className="kpiLabel">Underdog win rate</div>
              <div className="kpiValue">{pct(summary.underdog_win_rate)}</div>
            </div>

            <div className="kpiCard">
              <div className="kpiLabel">Favorite ROI ($1)</div>
              <div className="kpiValue">{money(summary.favorite_roi)}</div>
            </div>

            <div className="kpiCard">
              <div className="kpiLabel">Underdog ROI ($1)</div>
              <div className="kpiValue">{money(summary.underdog_roi)}</div>
            </div>
          </div>

          {summary.missing_dates.length > 0 && (
            <div className={`card missingBox`}>
              <div className="kpiLabel" style={{ marginBottom: 6 }}>
                No games found in DB for:
              </div>
              <div className="mono">{summary.missing_dates.join(", ")}</div>
            </div>
          )}
        </>
      )}

      {/* Strategy Performance */}
      <div className="section">
        <h3 className="sectionTitle">Strategy Performance</h3>

        <div className="tableWrap">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th}>Strategy</th>
                <th style={th}>Bets</th>
                <th style={th}>Wins</th>
                <th style={th}>Win %</th>
                <th style={th}>Profit</th>
                <th style={th}>ROI ($1)</th>
              </tr>
            </thead>
            <tbody>
              {strategyRows.map((r) => (
                <tr key={r.strategy}>
                  <td style={td}>{stratLabel(r.strategy)}</td>
                  <td style={td}>{r.n_bets}</td>
                  <td style={td}>{r.wins}</td>
                  <td style={td}>{pct(r.win_rate)}</td>
                  <td style={td}>{money(r.profit)}</td>
                  <td style={td}>{money(r.roi)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Strategy toggle row */}
        <div className="toolbarRow">
          <div className="pill">
            Strategy view: <b>{stratLabel(strategy)}</b>
          </div>

          {(["favorite", "underdog", "home", "away"] as StrategyName[]).map((s) => (
            <button key={s} className="btn" onClick={() => void loadStrategyOnly(s)} disabled={strategy === s || loading} type="button">
              {stratLabel(s)}
            </button>
          ))}

          <div className="toolbarRowRight">
            <span className="pill">
              Equity points: <b>{equity.length}</b> · Bets in buckets: <b>{nBetsInBuckets}</b>
            </span>
          </div>
        </div>

        {/* Charts layout */}
        <div className={chartsClass}>
          <div className="chartCard">
            <div className="chartCardHeader">
              <div className="chartTitle">Equity Curve (Favorite vs Underdog)</div>
              <div className="chartSubtitle">Cumulative profit over time (one $1 bet per decided game).</div>
            </div>
            <div className="chartBody">
              <EquityCurveChart start={start} end={end} />
            </div>
          </div>

          <div className="chartCard">
            <div className="chartCardHeader">
              <div className="chartTitle">ROI by Implied Probability Bucket ({stratLabel(strategy)})</div>
              <div className="chartSubtitle">
                Buckets group games by implied win probability (from odds). Above 0 is profitable, below 0 is unprofitable.
              </div>
            </div>
            <div className="chartBody">
              <RoiBucketsChart strategy={strategy} start={start} end={end} />
            </div>
          </div>
        </div>

        {/* ROI buckets table */}
        <div className="tableWrap">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th}>Bucket</th>
                <th style={th}>Bets</th>
                <th style={th}>Wins</th>
                <th style={th}>Win %</th>
                <th style={th}>Profit</th>
                <th style={th}>ROI ($1)</th>
              </tr>
            </thead>
            <tbody>
              {buckets.map((b) => (
                <tr key={b.bucket}>
                  <td style={td}>{b.bucket}</td>
                  <td style={td}>{b.n_bets}</td>
                  <td style={td}>{b.wins}</td>
                  <td style={td}>{pct(b.win_rate)}</td>
                  <td style={td}>{money(b.profit)}</td>
                  <td style={td}>{money(b.roi)}</td>
                </tr>
              ))}
              {buckets.length === 0 && (
                <tr>
                  <td style={td} colSpan={6}>
                    No bucket data in this range.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Equity table */}
        <div className="tableWrap">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th}>#</th>
                <th style={th}>Commence</th>
                <th style={th}>Bet P/L</th>
                <th style={th}>Cum P/L</th>
                <th style={th}>Cum ROI</th>
              </tr>
            </thead>
            <tbody>
              {equity.slice(0, 25).map((p) => (
                <tr key={p.game_index}>
                  <td style={td}>{p.game_index}</td>
                  <td style={td}>{p.commence_time ?? "—"}</td>
                  <td style={td}>{money(p.bet_profit)}</td>
                  <td style={td}>{money(p.cum_profit)}</td>
                  <td style={td}>{p.cum_roi == null ? "—" : pct(p.cum_roi)}</td>
                </tr>
              ))}
              {equity.length === 0 && (
                <tr>
                  <td style={td} colSpan={5}>
                    No decided games in this range yet (equity builds only after winners exist).
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {equity.length > 25 && <div style={{ marginTop: 6, fontSize: 12, opacity: 0.8 }}>Showing first 25 points.</div>}
        </div>
      </div>

      {/* Daily table */}
      <div className="section">
        <h3 className="sectionTitle">Daily</h3>
        <div className="tableWrap">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th}>Date</th>
                <th style={th}>Games (odds)</th>
                <th style={th}>Decided</th>
                <th style={th}>Fav win%</th>
                <th style={th}>Dog win%</th>
                <th style={th}>Fav ROI</th>
                <th style={th}>Dog ROI</th>
              </tr>
            </thead>
            <tbody>
              {daily.map((d) => (
                <tr key={d.date}>
                  <td style={td}>{d.date}</td>
                  <td style={td}>{d.n_games_with_odds}</td>
                  <td style={td}>{d.n_decided_games}</td>
                  <td style={td}>{pct(d.favorite_win_rate)}</td>
                  <td style={td}>{pct(d.underdog_win_rate)}</td>
                  <td style={td}>{money(d.favorite_roi)}</td>
                  <td style={td}>{money(d.underdog_roi)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}