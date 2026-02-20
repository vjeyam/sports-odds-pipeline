import type { GameRow } from "../lib/api";
import "../styles/games.css";

function fmtML(x: number | null) {
  if (x == null) return "—";
  return x > 0 ? `+${x}` : `${x}`;
}

function fmtScore(away: number | null | undefined, home: number | null | undefined) {
  if (away == null || home == null) return "—";
  return `${away}–${home}`;
}

function fmtTimeCT(iso: string | null | undefined) {
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

function statusText(row: GameRow) {
  return row.status ?? (row.completed === 1 ? "Final" : "Scheduled");
}

function isLive(row: GameRow) {
  return (row.status ?? "Scheduled") === "In Progress";
}

function isFinal(row: GameRow) {
  return row.completed === 1 || (row.status ?? "") === "Final";
}

function favoriteSide(row: GameRow): "away" | "home" | null {
  const a = row.best_away_price_american;
  const h = row.best_home_price_american;
  if (a == null || h == null) return null;
  if (a === h) return null;
  // More negative is the favorite
  return a < h ? "away" : "home";
}

function norm(s: string) {
  return s.trim().toLowerCase();
}

/**
 * Backend winner may be:
 *  - "home" | "away"
 *  - team name ("Indiana Pacers")
 */
function winnerSide(row: GameRow): "home" | "away" | null {
  const w = row.winner;
  if (!w) return null;

  if (w === "home" || w === "away") return w;

  // winner is a team name
  const wn = norm(w);
  const home = norm(row.home_team ?? "");
  const away = norm(row.away_team ?? "");

  if (wn === home) return "home";
  if (wn === away) return "away";

  // handle partial match (rare but helpful)
  if (home && wn.includes(home)) return "home";
  if (away && wn.includes(away)) return "away";

  return null;
}

function winnerLabel(row: GameRow): string | null {
  const ws = winnerSide(row);
  if (!ws) return null;
  return ws === "home" ? row.home_team : row.away_team;
}

function didUpset(row: GameRow): boolean {
  if (!isFinal(row)) return false;

  const fav = favoriteSide(row); // "home" | "away" concept but stored as away/home
  if (!fav) return false;

  const ws = winnerSide(row); // "home" | "away"
  if (!ws) return false;

  // map fav to same vocabulary
  const favSide = fav === "home" ? "home" : "away";
  return ws !== favSide;
}

function Badge({
  label,
  variant = "neutral",
}: {
  label: string;
  variant?: "neutral" | "good" | "warn" | "live";
}) {
  return <span className={`gBadge gBadge--${variant}`}>{label}</span>;
}

function rowKey(r: GameRow, idx: number) {
  if (r.odds_event_id) return r.odds_event_id;
  const t = r.start_time ?? r.commence_time ?? "no-time";
  const a = r.away_team ?? "no-away";
  const h = r.home_team ?? "no-home";
  return `${t}|${a}|${h}|${idx}`;
}

export function GamesTable({ rows, loading }: { rows: GameRow[]; loading?: boolean }) {
  const cleanRows = rows.filter((r) => r?.odds_event_id && r.odds_event_id.trim().length > 0);

  return (
    <div className="gList">
      {loading && <div className="gCard gCard--muted">Loading games…</div>}

      {!loading && cleanRows.length === 0 && (
        <div className="gCard gCard--muted">No games found for this date.</div>
      )}

      {cleanRows.map((r, idx) => {
        const timeToShow = r.start_time ?? r.commence_time;
        const fav = favoriteSide(r);
        const upset = didUpset(r);
        const winTeam = winnerLabel(r);

        return (
          <div key={rowKey(r, idx)} className="gCard">
            {/* Top row */}
            <div className="gTopRow">
              <div className="gTime">
                <b>{fmtTimeCT(timeToShow)}</b> <span className="gMuted">(CT)</span>
              </div>

              <div className="gBadges">
                {isLive(r) && <Badge label="Live" variant="live" />}
                {isFinal(r) && <Badge label="Final" variant="good" />}
                {!isLive(r) && !isFinal(r) && <Badge label="Scheduled" variant="neutral" />}
                {upset && <Badge label="Upset" variant="warn" />}
              </div>
            </div>

            {/* Teams */}
            <div className="gTeams">
              <div className="gTeamRow">
                <div className="gTeamLeft">
                  <div className="gTeamName">{r.away_team ?? "—"}</div>
                  {fav === "away" && <Badge label="Favorite" variant="neutral" />}
                </div>
                <div className="gTeamRight">
                  Away ML: <b>{fmtML(r.best_away_price_american)}</b>
                </div>
              </div>

              <div className="gTeamRow">
                <div className="gTeamLeft">
                  <div className="gTeamName">{r.home_team ?? "—"}</div>
                  {fav === "home" && <Badge label="Favorite" variant="neutral" />}
                </div>
                <div className="gTeamRight">
                  Home ML: <b>{fmtML(r.best_home_price_american)}</b>
                </div>
              </div>
            </div>

            {/* Results */}
            <div className="gBottomRow">
              <div>
                Score: <b>{fmtScore(r.away_score, r.home_score)}</b>
              </div>
              <div>
                Status: <b>{statusText(r)}</b>
                {isFinal(r) && winTeam ? (
                  <>
                    {" "}
                    • Winner: <b>{winTeam}</b>
                  </>
                ) : null}
              </div>
            </div>

            {/* Details */}
            <details className="gDetails">
              <summary>Details</summary>
              <div className="gDetailsBody">
                <div>
                  Odds event id: <span className="gMuted">{r.odds_event_id}</span>
                </div>
                <div>
                  Commence time: <span className="gMuted">{r.commence_time ?? "—"}</span>
                </div>
                <div>
                  Start time (ESPN): <span className="gMuted">{r.start_time ?? "—"}</span>
                </div>
              </div>
            </details>
          </div>
        );
      })}
    </div>
  );
}