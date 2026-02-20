import { useEffect, useState } from "react";
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

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [start, end]);

  return (
    <div>
      <div style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap" }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 12, opacity: 0.8 }}>Start</span>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            style={{ padding: 8 }}
          />
        </label>

        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 12, opacity: 0.8 }}>End</span>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            style={{ padding: 8 }}
          />
        </label>

        <button onClick={loadAll} disabled={loading} style={{ padding: "10px 14px" }}>
          {loading ? "Loading..." : "Reload Analytics"}
        </button>
      </div>

      <ErrorBox error={error} />

      {summary && (
        <>
          <div
            style={{
              marginTop: 16,
              display: "grid",
              gap: 12,
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            }}
          >
            <div style={{ border: "1px solid #eee", padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: 12, opacity: 0.8 }}>Games (odds)</div>
              <div style={{ fontSize: 20 }}>{summary.n_games_with_odds}</div>
            </div>

            <div style={{ border: "1px solid #eee", padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: 12, opacity: 0.8 }}>Decided games</div>
              <div style={{ fontSize: 20 }}>{summary.n_decided_games}</div>
            </div>

            <div style={{ border: "1px solid #eee", padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: 12, opacity: 0.8 }}>Favorite win rate</div>
              <div style={{ fontSize: 20 }}>{pct(summary.favorite_win_rate)}</div>
            </div>

            <div style={{ border: "1px solid #eee", padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: 12, opacity: 0.8 }}>Underdog win rate</div>
              <div style={{ fontSize: 20 }}>{pct(summary.underdog_win_rate)}</div>
            </div>

            <div style={{ border: "1px solid #eee", padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: 12, opacity: 0.8 }}>Favorite ROI ($1)</div>
              <div style={{ fontSize: 20 }}>{money(summary.favorite_roi)}</div>
            </div>

            <div style={{ border: "1px solid #eee", padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: 12, opacity: 0.8 }}>Underdog ROI ($1)</div>
              <div style={{ fontSize: 20 }}>{money(summary.underdog_roi)}</div>
            </div>
          </div>

          {summary.missing_dates.length > 0 && (
            <div style={{ marginTop: 16, padding: 12, border: "1px solid #eee", borderRadius: 8 }}>
              <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 6 }}>No games found in DB for:</div>
              <div style={{ fontFamily: "monospace", fontSize: 12 }}>{summary.missing_dates.join(", ")}</div>
            </div>
          )}
        </>
      )}

      {/* Strategy Performance */}
      <div style={{ marginTop: 24 }}>
        <h3 style={{ margin: "0 0 8px 0" }}>Strategy Performance</h3>

        <div style={{ marginTop: 8, overflowX: "auto" }}>
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

        {/* Equity Curve chart (Favorite vs Underdog) */}
        <div style={{ marginTop: 16 }}>
          <h4 style={{ margin: "0 0 8px 0" }}>Equity Curve (Favorite vs Underdog)</h4>
          <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
            <EquityCurveChart start={start} end={end} />
          </div>
        </div>

        {/* Strategy toggle controls (drives equity table + ROI buckets chart) */}
        <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ fontSize: 12, opacity: 0.8 }}>Strategy:</div>
          {(["favorite", "underdog", "home", "away"] as StrategyName[]).map((s) => (
            <button
              key={s}
              onClick={() => void loadStrategyOnly(s)}
              disabled={strategy === s || loading}
              style={{ padding: "8px 12px" }}
            >
              {stratLabel(s)}
            </button>
          ))}
          <div style={{ fontSize: 12, opacity: 0.8, marginLeft: "auto" }}>
            Equity points: {equity.length} · Bets in buckets: {nBetsInBuckets}
          </div>
        </div>

        {/* ROI buckets chart */}
        <div style={{ marginTop: 16 }}>
          <h4 style={{ margin: "0 0 8px 0" }}>ROI by Implied Probability Bucket ({stratLabel(strategy)})</h4>
          <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
            <RoiBucketsChart strategy={strategy} start={start} end={end} />
          </div>
        </div>

        {/* ROI buckets table (optional but completes “end-to-end”) */}
        <div style={{ marginTop: 12, overflowX: "auto" }}>
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
        <div style={{ marginTop: 12, overflowX: "auto" }}>
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

          {equity.length > 25 && (
            <div style={{ marginTop: 6, fontSize: 12, opacity: 0.8 }}>Showing first 25 points.</div>
          )}
        </div>
      </div>

      {/* Daily table */}
      <div style={{ marginTop: 24, overflowX: "auto" }}>
        <h3 style={{ margin: "0 0 8px 0" }}>Daily</h3>
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
  );
}