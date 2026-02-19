export type StrategyName = "favorite" | "underdog" | "home" | "away";

export type GameRow = {
  odds_event_id: string;
  commence_time: string | null;
  home_team: string;
  away_team: string;
  best_home_price_american: number | null;
  best_away_price_american: number | null;

  // results fields (nullable if not pulled / not started)
  status?: string | null;
  completed?: number | null;
  start_time?: string | null;

  home_score?: number | null;
  away_score?: number | null;

  winner?: string | null; // "home" | "away" | null depending on backend
};

export async function getGames(date: string): Promise<GameRow[]> {
  const qs = new URLSearchParams({ date });
  return apiGet<GameRow[]>(`/api/games?${qs.toString()}`);
}

export type RefreshOddsRequest = {
  sport?: string;
  regions?: string;
  bookmakers?: string | null;
  db?: string | null;
};

export type RefreshResultsRequest = {
  dates: string[]; // ["YYYY-MM-DD", ...]
  league?: string;
  db?: string | null;
};

export async function refreshOdds(req: RefreshOddsRequest = {}): Promise<any> {
  // defaults match backend defaults
  const body = {
    sport: req.sport ?? "basketball_nba",
    regions: req.regions ?? "us",
    bookmakers: req.bookmakers ?? null,
    db: req.db ?? null,
  };
  return apiPost(`/api/etl/odds-refresh`, body);
}

export async function refreshResults(dates: string[], league = "nba", db: string | null = null): Promise<any> {
  const body: RefreshResultsRequest = { dates, league, db };
  return apiPost(`/api/etl/results-refresh`, body);
}

export type AnalyticsSummary = {
  start: string;
  end: string;
  n_games_with_odds: number;
  n_decided_games: number;
  favorite_win_rate: number | null;
  underdog_win_rate: number | null;
  favorite_profit: number | null;
  underdog_profit: number | null;
  favorite_roi: number | null;
  underdog_roi: number | null;
  missing_dates: string[];
};

export type AnalyticsDailyRow = {
  date: string;
  n_games_with_odds: number;
  n_decided_games: number;
  favorite_win_rate: number | null;
  underdog_win_rate: number | null;
  favorite_profit: number | null;
  underdog_profit: number | null;
  favorite_roi: number | null;
  underdog_roi: number | null;
};

export type AnalyticsDailyResponse = {
  start: string;
  end: string;
  missing_dates: string[];
  daily: AnalyticsDailyRow[];
};

export async function getAnalyticsSummary(start: string, end: string): Promise<AnalyticsSummary> {
  const qs = new URLSearchParams({ start, end });
  return apiGet<AnalyticsSummary>(`/api/analytics/summary?${qs.toString()}`);
}

export async function getAnalyticsDaily(start: string, end: string): Promise<AnalyticsDailyResponse> {
  const qs = new URLSearchParams({ start, end });
  return apiGet<AnalyticsDailyResponse>(`/api/analytics/daily?${qs.toString()}`);
}

export type StrategySummaryRow = {
  strategy: StrategyName;
  n_bets: number;
  wins: number;
  profit: number | null;
  roi: number | null;
  win_rate: number | null;
};

export type StrategiesSummaryResponse = {
  start: string;
  end: string;
  strategies: StrategySummaryRow[];
};

export async function getStrategiesSummary(start: string, end: string): Promise<StrategiesSummaryResponse> {
  const qs = new URLSearchParams({ start, end });
  return apiGet<StrategiesSummaryResponse>(`/api/strategies/summary?${qs.toString()}`);
}

export type StrategyEquityPoint = {
  game_index: number;
  commence_time: string | null;
  bet_profit: number | null;
  cum_profit: number | null;
  cum_roi: number | null;
  picked_side?: string | null;
  winner?: string | null;
  odds_american?: number | null;
  odds_event_id?: string | null;
  espn_event_id?: string | null;
};

export type StrategyEquityResponse = {
  strategy: StrategyName;
  start: string;
  end: string;
  n_points: number;
  equity: StrategyEquityPoint[];
};

export async function getStrategyEquity(
  strategy: StrategyName,
  start: string,
  end: string
): Promise<StrategyEquityResponse> {
  const qs = new URLSearchParams({ strategy, start, end });
  return apiGet<StrategyEquityResponse>(`/api/strategies/equity?${qs.toString()}`);
}

export type RoiBucketRow = {
  bucket: string; // "0.55-0.60"
  bucket_lo: number;
  bucket_hi: number;
  n_bets: number;
  wins: number;
  win_rate: number | null;
  profit: number | null;
  roi: number | null;
};

export type StrategyRoiBucketsResponse = {
  strategy: StrategyName;
  start: string;
  end: string;
  step: number;
  p_min: number;
  p_max: number;
  n_bets_in_range: number;
  buckets: RoiBucketRow[];
};

export async function getStrategyRoiBuckets(
  strategy: StrategyName,
  start: string,
  end: string,
  step = 0.05,
  pMin = 0.40,
  pMax = 0.80
): Promise<StrategyRoiBucketsResponse> {
  const qs = new URLSearchParams({
    strategy,
    start,
    end,
    step: String(step),
    p_min: String(pMin),
    p_max: String(pMax),
  });
  return apiGet<StrategyRoiBucketsResponse>(`/api/strategies/roi-buckets?${qs.toString()}`);
}

async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`Request failed (${r.status}) for ${path}`);
  return (await r.json()) as T;
}

async function apiPost<T>(path: string, body: any): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!r.ok) throw new Error(`Request failed (${r.status}) for ${path}`);
  return (await r.json()) as T;
}