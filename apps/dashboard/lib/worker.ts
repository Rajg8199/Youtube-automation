// Server-side worker API client. Runs only on the server (no browser CORS).

const WORKER_URL = process.env.WORKER_URL ?? "http://localhost:8008";

export interface ScoredTopic {
  id: string;
  title: string;
  category: string | null;
  devices: string[] | null;
  brands: string[] | null;
  summary: string | null;
  status: string;
  signal_count: number;
  composite: number;
  rationale: string | null;
  trend_velocity: number;
  search_demand: number;
  competition_gap: number;
  channel_fit: number;
  monetization_potential: number;
  freshness: number;
  predicted_views_score: number;
}

export interface Signal {
  id: string;
  title: string;
  url: string | null;
  source: string | null;
  published_at: string | null;
  fetched_at: string;
  processed: boolean;
}

export async function getScoredTopics(limit = 100): Promise<ScoredTopic[]> {
  const res = await fetch(`${WORKER_URL}/topics/scored?limit=${limit}`, {
    cache: "no-store",
  });
  if (!res.ok) return [];
  return (await res.json()).topics ?? [];
}

export async function getRecentSignals(limit = 50): Promise<Signal[]> {
  const res = await fetch(`${WORKER_URL}/signals/recent?limit=${limit}`, {
    cache: "no-store",
  });
  if (!res.ok) return [];
  return (await res.json()).signals ?? [];
}

export async function decideTopic(
  id: string,
  action: "greenlight" | "reject",
): Promise<Response> {
  return fetch(`${WORKER_URL}/topics/${id}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
}
