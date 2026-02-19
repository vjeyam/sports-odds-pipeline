import { useEffect, useState } from "react";
import { getGames, refreshResults, refreshOdds, type GameRow } from "./lib/api";
import "./App.css";

function fmtScore(away: number | null, home: number | null) {
  if (away == null || home == null) return "—";
  return `${away} - ${home}`;
}

function statusLabel(row: GameRow) {
  return row.status ?? "Scheduled";
}

function fmtML(x: number | null) {
  if (x == null) return "—";
  return x > 0 ? `+${x}` : `${x}`;
}

function fmtTime(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    timeZone: "America/Chicago",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function todayISO(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export default function App() {
  const [date, setDate] = useState(todayISO());
  const [rows, setRows] = useState<GameRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [oddsRefreshing, setOddsRefreshing] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getGames(date);
      setRows(data);
    } catch (e) {
      setRows([]);
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function onRefreshResults() {
    setRefreshing(true);
    setError(null);
    try {
      await refreshResults([date]);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setRefreshing(false);
    }
  }

  async function onRefreshOdds() {
    try {
      setOddsRefreshing(true);
      await refreshOdds();
      await load();
    } catch (e: any) {
      alert(`Error refreshing odds: ${e?.message ?? e}`);
    } finally {
      setOddsRefreshing(false);
    }
  }

  useEffect(() => { void load(); }, [date]);

  const th: React.CSSProperties = {
    textAlign: "left",
    borderBottom: "1px solid #ddd",
    padding: 8,
    whiteSpace: "nowrap",
  };

  const td: React.CSSProperties = {
    borderBottom: "1px solid #f0f0f0",
    padding: 8,
    whiteSpace: "nowrap",
  };

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      <h2>Games</h2>

      <div style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap" }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 12, opacity: 0.8 }}>Date</span>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            style={{ padding: 8 }}
          />
        </label>

        <button
          onClick={onRefreshResults}
          disabled={loading || refreshing}
          style={{ padding: "10px 14px" }}
          title="Runs results ETL for the selected date"
        >
          {refreshing ? "Refreshing..." : "Refresh Results"}
        </button>

        <button onClick={onRefreshOdds} disabled={oddsRefreshing}>
          {oddsRefreshing ? "Refreshing Odds..." : "Refresh Odds"}
        </button>

        <button onClick={load} disabled={loading || refreshing} style={{ padding: "10px 14px" }}>
          {loading ? "Loading..." : "Reload"}
        </button>

        <div style={{ marginLeft: "auto", fontSize: 12, opacity: 0.8 }}>
          Rows: {rows.length}
        </div>
      </div>

      {error && (
        <div style={{ marginTop: 12, padding: 12, border: "1px solid #f99" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <div style={{ marginTop: 16, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>Time (CT)</th>
              <th style={th}>Away</th>
              <th style={th}>Home</th>
              <th style={th}>Away ML</th>
              <th style={th}>Home ML</th>
              <th style={th}>Score</th>
              <th style={th}>Winner</th>
              <th style={th}>Status</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((r) => {
              const isFinal = r.completed === 1;
              const timeToShow = r.start_time ?? r.commence_time;

              return (
                <tr key={r.odds_event_id}>
                  <td style={td}>{fmtTime(timeToShow)}</td>
                  <td style={td}>{r.away_team ?? "—"}</td>
                  <td style={td}>{r.home_team ?? "—"}</td>
                  <td style={td}>{fmtML(r.best_away_price_american)}</td>
                  <td style={td}>{fmtML(r.best_home_price_american)}</td>
                  <td style={td}>{fmtScore(r.away_score, r.home_score)}</td>

                  {/* winner only when completed */}
                  <td style={td}>{isFinal ? (r.winner ?? "—") : "—"}</td>

                  {/* use backend-provided status */}
                  <td style={td}>{statusLabel(r)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
