export type JoinedGameRow = {
  odds_event_id: string;
  espn_event_id: string;
  commence_time: string | null;
  home_team: string | null;
  away_team: string | null;
  best_home_price_american: number | null;
  best_away_price_american: number | null;
  home_score: number | null;
  away_score: number | null;
  winner: string | null;
  favorite_side: string | null;
  underdog_side: string | null;
};

export type GameRow = {
  odds_event_id: string;
  commence_time: string | null;
  home_team: string | null;
  away_team: string | null;
  best_home_price_american: number | null;
  best_away_price_american: number | null;
  home_score: number | null;
  away_score: number | null;
  winner: string | null;
};

export async function getGames(date: string): Promise<GameRow[]> {
  const res = await fetch(`/api/games?date=${encodeURIComponent(date)}`);
  if (!res.ok) throw new Error(`GET /api/games failed: ${res.status}`);
  return (await res.json()) as GameRow[];
}

export async function getJoinedGames(date: string): Promise<JoinedGameRow[]> {
  const res = await fetch(`/api/games/joined?date=${encodeURIComponent(date)}`);
  if (!res.ok) throw new Error(`GET /api/games/joined failed: ${res.status}`);
  return (await res.json()) as JoinedGameRow[];
}

export async function refreshResults(dates: string[]): Promise<unknown> {
  const res = await fetch(`/api/etl/results-refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dates }),
  });
  if (!res.ok) throw new Error(`POST /api/etl/results-refresh failed: ${res.status}`);
  return await res.json();
}
