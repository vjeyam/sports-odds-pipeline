import { useEffect, useState } from "react";
import "./App.css";
import { getJoinedGames, refreshResults, type JoinedGameRow } from "./lib/api";

function todayISO(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function fmtTime(s: string | null): string {
  if (!s) return "";
  // keep it simple; you can prettify later
  return s.replace("T", " ").replace("Z", "");
}

export default function App() {
  const [date, setDate] = useState(todayISO());
  const [rows, setRows] = useState<JoinedGameRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getJoinedGames(date);
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
      await load(); // reload table after ETL refresh
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date]);

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
        >
          {refreshing ? "Refreshing..." : "Refresh Results"}
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
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>
                Time
              </th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>
                Away
              </th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>
                Home
              </th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>
                Away ML
              </th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>
                Home ML
              </th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>
                Score
              </th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>
                Winner
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.odds_event_id}>
                <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>
                  {fmtTime(r.commence_time)}
                </td>
                <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>{r.away_team}</td>
                <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>{r.home_team}</td>
                <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>
                  {r.best_away_price_american ?? ""}
                </td>
                <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>
                  {r.best_home_price_american ?? ""}
                </td>
                <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>
                  {r.away_score ?? ""}{r.away_score != null || r.home_score != null ? " - " : ""}
                  {r.home_score ?? ""}
                </td>
                <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>{r.winner ?? ""}</td>
              </tr>
            ))}

            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={7} style={{ padding: 12, opacity: 0.8 }}>
                  No games returned for {date}. Try a different date or run “Refresh Results”.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
