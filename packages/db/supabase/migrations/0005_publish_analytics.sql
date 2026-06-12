-- 0005_publish_analytics.sql
-- Publishing & analytics: publish jobs, youtube videos, metrics, retention, comments, competitors.

create table publish_jobs (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid references content_items(id) on delete cascade,
  method text check (method in ('api','manual_kit')),
  scheduled_at timestamptz,
  attempted_at timestamptz,
  youtube_video_id text,
  quota_cost int default 0,
  status text default 'pending' check (status in ('pending','uploading','done','failed','quota_blocked')),
  error text
);

create table youtube_videos (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid references content_items(id),
  youtube_video_id text unique not null,
  published_at timestamptz,
  format text,
  duration_sec int,
  topic_embedding vector(1024),            -- for the learning loop
  hook_embedding vector(1024)
);

create table video_metrics_daily (
  id bigint generated always as identity primary key,
  youtube_video_id text not null,
  date date not null,
  views bigint, impressions bigint, ctr numeric,
  avg_view_duration_sec numeric, avg_pct_viewed numeric,
  watch_time_min numeric, likes int, comments int, shares int,
  subs_gained int, subs_lost int,
  estimated_revenue_usd numeric,
  traffic_sources jsonb,                   -- {browse, search, suggested, shorts_feed...}
  unique (youtube_video_id, date)
);

create table retention_curves (
  id bigint generated always as identity primary key,
  youtube_video_id text not null,
  captured_at timestamptz default now(),
  curve jsonb not null                     -- [{pct_position, audience_retention}]
);

create table channel_snapshots (
  id bigint generated always as identity primary key,
  date date unique not null,
  subscribers bigint, total_views bigint, total_watch_time_min numeric,
  videos_published int, estimated_revenue_usd numeric,
  raw jsonb
);

create table comments_intel (
  id uuid primary key default gen_random_uuid(),
  youtube_video_id text,
  comment_id text unique,
  text text, author text, likes int,
  sentiment text, intent text,             -- question | request | complaint | praise
  video_idea_extracted text,
  needs_reply boolean default false,
  suggested_reply text,
  created_at timestamptz default now()
);

create table competitors (
  id uuid primary key default gen_random_uuid(),
  channel_id text unique not null,
  name text, subscribers bigint,
  last_checked timestamptz
);

create table competitor_videos (
  id uuid primary key default gen_random_uuid(),
  competitor_id uuid references competitors(id),
  youtube_video_id text unique,
  title text, published_at timestamptz,
  views bigint, topic_embedding vector(1024)
);
