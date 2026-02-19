import { useEffect, useRef, useState } from "react";
import { 
  getGames,
  refreshOdds,
  refreshResults,
  type GameRow
} from "../lib/api";
import { ErrorBox } from "../components/ErrorBox";
import { GamesTable } from "../components/GamesTable";

function todayISO(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function hasLiveGames(rows: GameRow[]) {
  return rows.some((r) => (r.status ?? "Scheduled") === "In Progress");
}

export default function GamesPage() {
  const [date, setDate] = useState(todayISO());
  const [rows, setRows] = useState<GameRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [oddsRefreshing, setOddsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadingRef = useRef(false);
  const live = hasLiveGames(rows);

  async function load() {
    if (loadingRef.current) return;
    loadingRef.current = true;

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
      loadingRef.current = false;
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

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date]);

  useEffect(() => {
    if (!hasLiveGames(rows)) return;

    const id = window.setInterval(() => {
      void load();
    }, 30_000);

    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, date]);

  return (
    <div>
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

        <button onClick={onRefreshOdds} disabled={oddsRefreshing} style={{ padding: "10px 14px" }}>
          {oddsRefreshing ? "Refreshing Odds..." : "Refresh Odds"}
        </button>

        <button onClick={load} disabled={loading || refreshing} style={{ padding: "10px 14px" }}>
          {loading ? "Loading..." : "Reload"}
        </button>

        <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
          {live && <div style={{ fontSize: 12, opacity: 0.8 }}>Live games — auto-refreshing</div>}
          <div style={{ fontSize: 12, opacity: 0.8 }}>Rows: {rows.length}</div>
        </div>
      </div>

      <ErrorBox error={error} />
      <GamesTable rows={rows} />
    </div>
  );
}
