// Server-side worker API client. Runs only on the server (no browser CORS).

const WORKER_URL = process.env.WORKER_URL ?? "http://localhost:8008";

/** Browser-reachable base for <audio>/<video>/<img> media tags. */
export const mediaBase = WORKER_URL;

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

export interface ScriptItem {
  id: string;
  working_title: string;
  angle: string | null;
  format: string;
  status: string;
  version: number | null;
  hook: string | null;
  body_markdown: string | null;
  cta: string | null;
  word_count: number | null;
  est_duration_sec: number | null;
  passed: boolean | null;
  claims_checked: number | null;
  claims_failed: { claim: string; reason: string }[] | null;
  policy_flags: { type: string; note: string }[] | null;
  readability_notes: string | null;
  approval_status: string | null;
}

export async function getScripts(limit = 100): Promise<ScriptItem[]> {
  const res = await fetch(`${WORKER_URL}/scripts?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) return [];
  return (await res.json()).scripts ?? [];
}

export async function decideScript(
  id: string,
  action: "approve" | "request_changes" | "reject",
  note?: string,
): Promise<Response> {
  return fetch(`${WORKER_URL}/content/${id}/script-decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, note }),
  });
}

export interface SceneEntry {
  idx: number;
  template: string;
  caption: string;
  duration: number;
}
export interface ThumbVariant {
  variant: string;
  path: string;
  selected: boolean;
  concept: string;
}
export interface StudioItem {
  id: string;
  working_title: string;
  format: string;
  status: string;
  voiceover_path: string | null;
  voiceover_duration: number | null;
  video_path: string | null;
  video_duration: number | null;
  scenes: SceneEntry[] | null;
  thumbnails: ThumbVariant[] | null;
}

export async function getStudioItems(limit = 50): Promise<StudioItem[]> {
  const res = await fetch(`${WORKER_URL}/studio?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) return [];
  return (await res.json()).studio ?? [];
}

export interface PublishQuota {
  used: number;
  remaining: number;
  daily: number;
  youtube_ready: boolean;
}
export interface PublishItem {
  id: string;
  working_title: string;
  status: string;
  title: string | null;
  tag_count: number | null;
  video_path: string | null;
  method: string | null;
  publish_status: string | null;
  youtube_video_id: string | null;
  publish_note: string | null;
  approval_status: string | null;
  kit_path: string | null;
}

export async function getPublishQueue(): Promise<{ quota: PublishQuota | null; items: PublishItem[] }> {
  const res = await fetch(`${WORKER_URL}/publish`, { cache: "no-store" });
  if (!res.ok) return { quota: null, items: [] };
  const j = await res.json();
  return { quota: j.quota ?? null, items: j.items ?? [] };
}

export async function decidePublish(id: string, action: "approve" | "reject"): Promise<Response> {
  return fetch(`${WORKER_URL}/content/${id}/publish-decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
}

export interface PublishedVideo {
  youtube_video_id: string;
  published_at: string | null;
  format: string | null;
  working_title: string | null;
  views: number | null;
  watch_time_min: number | null;
  avg_pct_viewed: number | null;
  likes: number | null;
  comments: number | null;
  metrics_date: string | null;
}

export async function getVideos(limit = 50): Promise<PublishedVideo[]> {
  const res = await fetch(`${WORKER_URL}/videos?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) return [];
  return (await res.json()).videos ?? [];
}
