/**
 * @pwg/db — migrations live in supabase/migrations (applied via `make db-reset`).
 * This module exposes table-name constants now; a generated typed client
 * (supabase-js / kysely types) is added in Phase 1 once schema stabilizes.
 */

export const TABLES = {
  sources: "sources",
  rawSignals: "raw_signals",
  topics: "topics",
  topicScores: "topic_scores",
  launchCalendar: "launch_calendar",
  contentItems: "content_items",
  pipelineEvents: "pipeline_events",
  researchBriefs: "research_briefs",
  scripts: "scripts",
  scriptQaReports: "script_qa_reports",
  mediaAssets: "media_assets",
  scenePlans: "scene_plans",
  thumbnails: "thumbnails",
  seoMetadata: "seo_metadata",
  publishJobs: "publish_jobs",
  youtubeVideos: "youtube_videos",
  videoMetricsDaily: "video_metrics_daily",
  retentionCurves: "retention_curves",
  channelSnapshots: "channel_snapshots",
  commentsIntel: "comments_intel",
  competitors: "competitors",
  competitorVideos: "competitor_videos",
  insights: "insights",
  recommendations: "recommendations",
  agentRuns: "agent_runs",
  costs: "costs",
  approvals: "approvals",
  autonomySettings: "autonomy_settings",
  systemEvents: "system_events",
  quotaLedger: "quota_ledger",
} as const;

export type TableName = (typeof TABLES)[keyof typeof TABLES];

/** Expected object counts — asserted by scripts/db-verify.sh. */
export const EXPECTED_TABLE_COUNT = Object.keys(TABLES).length; // 30
