-- 0002_research.sql
-- Research layer: sources, raw signals, topics, scoring, launch calendar.

create table sources (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  type text not null check (type in ('rss','api','reddit','youtube_channel','scrape','manual')),
  url text,
  config jsonb default '{}',
  trust_score numeric default 0.5,        -- learned reliability 0..1
  active boolean default true,
  last_polled_at timestamptz,
  created_at timestamptz default now()
);

create table raw_signals (
  id uuid primary key default gen_random_uuid(),
  source_id uuid references sources(id),
  external_id text,                       -- dedupe key
  title text not null,
  url text,
  content text,
  published_at timestamptz,
  fetched_at timestamptz default now(),
  embedding vector(1024),
  processed boolean default false,
  unique (source_id, external_id)
);

create table topics (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  slug text unique,
  category text check (category in ('launch','leak','comparison','review','buying_guide','news','ai_feature','android_tips','explainer')),
  devices text[] default '{}',            -- e.g. {'Samsung Galaxy S26','OnePlus 14'}
  brands text[] default '{}',
  summary text,
  signal_ids uuid[] default '{}',         -- clustered raw_signals
  embedding vector(1024),
  status text default 'new' check (status in ('new','scored','selected','rejected','expired','converted')),
  expires_at timestamptz,                 -- leaks/news go stale
  created_at timestamptz default now()
);

create table topic_scores (
  id uuid primary key default gen_random_uuid(),
  topic_id uuid references topics(id) on delete cascade,
  trend_velocity numeric,                 -- signal volume growth
  search_demand numeric,                  -- proxy: autosuggest depth, news volume
  competition_gap numeric,                -- competitor coverage inverse
  channel_fit numeric,                    -- similarity to channel's best performers (pgvector)
  monetization_potential numeric,         -- affiliate-able devices, buying intent
  freshness numeric,
  predicted_views_score numeric,          -- model output from learning loop
  composite numeric not null,
  rationale text,
  scored_at timestamptz default now()
);

create table launch_calendar (
  id uuid primary key default gen_random_uuid(),
  device text not null,
  brand text,
  event_date date,
  confidence text check (confidence in ('confirmed','rumored')),
  notes text,
  coverage_plan jsonb default '[]',       -- planned videos: pre-launch, live, review...
  created_at timestamptz default now()
);
