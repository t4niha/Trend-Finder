export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface KeyEntities {
  companies?: string[];
  products?: string[];
  people?: string[];
}

export interface Trend {
  rank: number;
  title: string;
  description: string;
  key_entities?: KeyEntities;
  sentiment?: "positive" | "negative" | "mixed" | string;
  importance?: string;
  references?: string[];
}

export interface WeekResult {
  week_number: number;
  week_label: string;
  post_count: number;
  clusters_found: number;
  noise_posts: number;
  trends: Trend[];
}

export interface TrendResponse {
  niche: string;
  week: number | null;
  results: WeekResult[];
}

export interface NicheSummary {
  niche: string;
  total_posts: number;
  weeks_available: number[];
  total_trends: number;
}

export interface NichesResponse {
  generated_at?: string;
  model?: string;
  niches: NicheSummary[];
}

export const nicheMeta: Record<string, { emoji: string; label: string }> = {
  technology: { emoji: "🖥", label: "Technology" },
  science: { emoji: "🔬", label: "Science" },
  worldnews: { emoji: "🌍", label: "World News" },
  gaming: { emoji: "🎮", label: "Gaming" },
  smartphones: { emoji: "📱", label: "Smartphones" },
  movies: { emoji: "🎬", label: "Movies" },
};

export function getNicheLabel(niche: string) {
  return nicheMeta[niche]?.label ?? niche.replace(/-/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export async function fetchNiches(signal?: AbortSignal) {
  const response = await fetch(`${API_BASE}/api/v1/niches`, {
    signal,
    headers: { accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Could not load niches (${response.status})`);
  return (await response.json()) as NichesResponse;
}

export async function fetchTrends(niche: string, week?: string | number, signal?: AbortSignal) {
  const weekQuery = week === undefined ? "" : `?week=${week}`;
  const response = await fetch(`${API_BASE}/api/v1/trends/${encodeURIComponent(niche)}${weekQuery}`, {
    signal,
    headers: { accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Could not load trends (${response.status})`);
  return (await response.json()) as TrendResponse;
}
