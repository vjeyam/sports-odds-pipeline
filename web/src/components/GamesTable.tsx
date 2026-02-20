import type { GameRow } from "../lib/api";
import { th, td } from "../styles/ui";

function fmtScore(away: number | null, home: number | null) {
  if (away == null || home == null) return "—";
  return `${away} - ${home}`;
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

function statusLabel(row: GameRow) {
  return row.status ?? "Scheduled";
}

function rowKey(r: GameRow, idx: number) {
  // Primary key
  if (r.odds_event_id) return r.odds_event_id;

  // Fallback: deterministic composite key (should rarely be needed)
  const t = r.start_time ?? r.commence_time ?? "no-time";
  const a = r.away_team ?? "no-away";
  const h = r.home_team ?? "no-home";
  return `${t}|${a}|${h}|${idx}`;
}

export function GamesTable({ rows }: { rows: GameRow[] }) {
  const cleanRows = rows.filter(r => r?.odds_event_id && r.odds_event_id.trim().length > 0);

  return (
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
          {cleanRows.map((r, idx) => {
            const isFinal = r.completed === 1;
            const timeToShow = r.start_time ?? r.commence_time;

            return (
              <tr key={rowKey(r, idx)}>
                <td style={td}>{fmtTime(timeToShow)}</td>
                <td style={td}>{r.away_team ?? "—"}</td>
                <td style={td}>{r.home_team ?? "—"}</td>
                <td style={td}>{fmtML(r.best_away_price_american)}</td>
                <td style={td}>{fmtML(r.best_home_price_american)}</td>
                <td style={td}>{fmtScore(r.away_score, r.home_score)}</td>

                {/* winner only when completed */}
                <td style={td}>{isFinal ? (r.winner ?? "—") : "—"}</td>

                <td style={td}>{statusLabel(r)}</td>
              </tr>
            );
          })}

          {cleanRows.length === 0 && (
            <tr>
              <td style={td} colSpan={8}>
                No games found for this date.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
