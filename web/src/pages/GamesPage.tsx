import { useEffect, useMemo, useRef, useState } from "react";
import { getGames, refreshOdds, refreshResults, type GameRow } from "../lib/api";
import { ErrorBox } from "../components/ErrorBox";
import { GamesTable } from "../components/GamesTable";
import "../styles/gamesPage.css";

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

  const stats = useMemo(() => {
    const total = rows.length;
    const completed = rows.filter((r) => r.completed === 1).length;
    const inProgress = rows.filter((r) => (r.status ?? "Scheduled") === "In Progress").length;
    return { total, completed, inProgress };
  }, [rows]);

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
    <div className="gpPage">
      {/* Header */}
      <div className="gpHeader">
        <div className="gpTitle">Games & Odds</div>
        <div className="gpSubtitle">
          You’re viewing the <b>best available moneyline</b> across sportsbooks for each game.
          Odds are shown in <b>American format</b> (e.g. <b>-180</b> favorite, <b>+160</b> underdog).
        </div>
      </div>

      {/* Controls */}
      <div className="gpControls">
        <label className="gpField">
          <span className="gpLabel">Date</span>
          <input
            className="gpDateInput"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>

        <button
          className="gpBtn"
          onClick={onRefreshResults}
          disabled={loading || refreshing}
          title="Runs results ETL for the selected date"
        >
          {refreshing ? "Refreshing Results..." : "Refresh Results"}
        </button>

        <button className="gpBtn" onClick={onRefreshOdds} disabled={oddsRefreshing}>
          {oddsRefreshing ? "Refreshing Odds..." : "Refresh Odds"}
        </button>

        <button className="gpBtn" onClick={load} disabled={loading || refreshing}>
          {loading ? "Loading..." : "Reload"}
        </button>

        <div className="gpRight">
          {live && (
            <div
              className="gpLivePill"
              title="This page will auto-refresh every 30 seconds while games are live"
            >
              Live games — auto-refreshing
            </div>
          )}

          <div className="gpStats">
            <span>
              Games: <b>{stats.total}</b>
            </span>
            <span>
              Completed: <b>{stats.completed}</b>
            </span>
            <span>
              Live: <b>{stats.inProgress}</b>
            </span>
          </div>
        </div>
      </div>

      <ErrorBox error={error} />
      <GamesTable rows={rows} loading={loading} />
    </div>
  );
}