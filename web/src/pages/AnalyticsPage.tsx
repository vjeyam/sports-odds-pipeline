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
import StrategyEquityChart from "../components/StrategyEquityChart";
import DailyRoiChart from "../components/DailyRoiChart";
import { th, td } from "../styles/ui";

import "../styles/analytics.css";

const MIN_DATE = "2026-02-19"; // earliest allowed date (local ISO YYYY-MM-DD)

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

function clampISODate(d: string, min: string, max: string): string {
  if (!d) return min;
  if (d < min) return min;
  if (d > max) return max;
  return d;
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
  const maxDate = todayISO();

  // Default start = max(MIN_DATE, today-7)
  const defaultStart = useMemo(() => {
    const s = isoDaysAgo(7);
    return s < MIN_DATE ? MIN_DATE : s;
  }, []);
  const defaultEnd = useMemo(() => {
    return maxDate < MIN_DATE ? MIN_DATE : maxDate;
  }, [maxDate]);

  const [start, setStart] = useState(() => defaultStart);
  const [end, setEnd] = useState(() => defaultEnd);
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

  async function loadAll(nextStart = start, nextEnd = end, nextStrategy = strategy) {
    setLoading(true);
    setError(null);

    try {
      const [s, d, stratSummary, stratEquity, stratBuckets] = await Promise.all([
        getAnalyticsSummary(nextStart, nextEnd),
        getAnalyticsDaily(nextStart, nextEnd),
        getStrategiesSummary(nextStart, nextEnd),
        getStrategyEquity(nextStrategy, nextStart, nextEnd),
        getStrategyRoiBuckets(nextStrategy, nextStart, nextEnd),
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
      const [eq, rb] = await Promise.all([
        getStrategyEquity(next, start, end),
        getStrategyRoiBuckets(next, start, end),
      ]);
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
    const max = todayISO();
    const rawStart = isoDaysAgo(days);
    const nextStart = clampISODate(rawStart, MIN_DATE, max);
    const nextEnd = clampISODate(max, MIN_DATE, max);

    // If nextStart somehow ends up after end, clamp it
    const finalStart = nextStart > nextEnd ? nextEnd : nextStart;

    setStart(finalStart);
    setEnd(nextEnd);
  }

  // Keep start/end always clamped (covers manual typing)
  useEffect(() => {
    const max = todayISO();

    const clampedStart = clampISODate(start, MIN_DATE, max);
    const clampedEnd = clampISODate(end, MIN_DATE, max);

    // Ensure start <= end
    const finalStart = clampedStart > clampedEnd ? clampedEnd : clampedStart;

    if (finalStart !== start) setStart(finalStart);
    if (clampedEnd !== end) setEnd(clampedEnd);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [start, end]);

  // Load whenever range changes
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
            <input
              className="input"
              type="date"
              value={start}
              min={MIN_DATE}
              max={maxDate}
              onChange={(e) => {
                const max = todayISO();
                const next = clampISODate(e.target.value, MIN_DATE, max);
                // keep start <= end
                setStart(next > end ? end : next);
              }}
            />
          </label>

          <label className="field">
            <span className="fieldLabel">End</span>
            <input
              className="input"
              type="date"
              value={end}
              min={MIN_DATE}
              max={maxDate}
              onChange={(e) => {
                const max = todayISO();
                const next = clampISODate(e.target.value, MIN_DATE, max);
                // keep start <= end
                setEnd(next < start ? start : next);
              }}
            />
          </label>

          <button className="btn" onClick={() => void loadAll()} disabled={loading}>
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
            <button
              key={s}
              className="btn"
              onClick={() => void loadStrategyOnly(s)}
              disabled={strategy === s || loading}
              type="button"
            >
              {stratLabel(s)}
            </button>
          ))}

          <div className="toolbarRowRight">
            <span className="pill">
              Equity points: <b>{equity.length}</b> · Bets in buckets: <b>{nBetsInBuckets}</b>
            </span>
          </div>
        </div>

        {/* Charts row 1 */}
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

        {/* Charts row 2 */}
        <div className={chartsClass} style={{ marginTop: 12 }}>
          <div className="chartCard">
            <div className="chartCardHeader">
              <div className="chartTitle">Selected Strategy Equity ({stratLabel(strategy)})</div>
              <div className="chartSubtitle">Cumulative P/L for the currently selected strategy.</div>
            </div>
            <div className="chartBody">
              <StrategyEquityChart strategy={strategy} equity={equity} />
            </div>
          </div>

          <div className="chartCard">
            <div className="chartCardHeader">
              <div className="chartTitle">Daily Trend</div>
              <div className="chartSubtitle">Switch between ROI and estimated profit.</div>
            </div>
            <div className="chartBody">
              <DailyRoiChart daily={daily} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}