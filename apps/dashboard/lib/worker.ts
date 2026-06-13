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

export interface Overview {
  kpis: {
    topics_scored: number;
    topics_greenlit: number;
    in_flight: number;
    published_videos: number;
    cost_mtd_usd: number;
    monthly_cap_usd: number;
    stack_tier: string;
  };
  quota: { used: number; remaining: number; daily: number };
  funnel: { status: string; count: number }[];
  recent: { severity: string; component: string; message: string; created_at: string }[];
}

export async function getOverview(): Promise<Overview | null> {
  try {
    const res = await fetch(`${WORKER_URL}/overview`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export interface Insight {
  id: string;
  scope: string;
  insight: string;
  confidence: number | null;
  applied: boolean;
}
export interface Recommendation {
  id: string;
  type: string;
  title: string;
  detail: string | null;
  status: string;
}
export interface AutonomyGate {
  gate: string;
  mode: string;
  updated_at: string;
}
export interface Guardrails {
  published: number;
  qa_pass_rate: number;
  policy_flags_30d: number;
  full_auto_eligible: boolean;
  thresholds: { min_published: number; min_qa_pass_rate: number };
}

export async function getInsights(): Promise<{ insights: Insight[]; recommendations: Recommendation[] }> {
  const res = await fetch(`${WORKER_URL}/insights`, { cache: "no-store" });
  if (!res.ok) return { insights: [], recommendations: [] };
  const j = await res.json();
  return { insights: j.insights ?? [], recommendations: j.recommendations ?? [] };
}

export async function getAutonomy(): Promise<{ gates: AutonomyGate[]; guardrails: Guardrails | null }> {
  const res = await fetch(`${WORKER_URL}/autonomy`, { cache: "no-store" });
  if (!res.ok) return { gates: [], guardrails: null };
  const j = await res.json();
  return { gates: j.gates ?? [], guardrails: j.guardrails ?? null };
}

export async function setAutonomy(gate: string, mode: string): Promise<Response> {
  return fetch(`${WORKER_URL}/autonomy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gate, mode }),
  });
}
