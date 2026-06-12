-- 0006_learning_ops.sql
-- Learning, ops, governance: insights, recommendations, agent runs, costs, approvals, autonomy, events, quota.

create table insights (
  id uuid primary key default gen_random_uuid(),
  scope text check (scope in ('video','topic','thumbnail','hook','schedule','channel')),
  ref_id text,
  insight text not null,
  evidence jsonb,
  confidence numeric,
  actionable boolean default true,
  applied boolean default false,
  created_at timestamptz default now()
);

create table recommendations (
  id uuid primary key default gen_random_uuid(),
  type text check (type in ('topic','format','schedule','thumbnail_style','hook_style','series')),
  title text not null,
  detail text,
  expected_impact text,
  status text default 'proposed' check (status in ('proposed','accepted','rejected','done')),
  created_at timestamptz default now()
);

create table agent_runs (
  id uuid primary key default gen_random_uuid(),
  agent text not null,
  content_item_id uuid,
  model text, input_tokens int, output_tokens int,
  cost_usd numeric, latency_ms int,
  status text check (status in ('ok','error','retried')),
  error text,
  created_at timestamptz default now()
);

create table costs (
  id bigint generated always as identity primary key,
  category text check (category in ('llm','tts','video_gen','render','storage','api','infra')),
  content_item_id uuid,
  amount_usd numeric not null,
  detail jsonb,
  created_at timestamptz default now()
);

create table approvals (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid references content_items(id) on delete cascade,
  gate text check (gate in ('script','publish')),
  status text default 'pending' check (status in ('pending','approved','rejected','changes_requested')),
  reviewer_note text,
  decided_at timestamptz,
  created_at timestamptz default now()
);

create table autonomy_settings (
  gate text primary key,                   -- 'script' | 'publish' | 'topic_selection'
  mode text default 'manual' check (mode in ('manual','auto_with_veto','full_auto')),
  updated_at timestamptz default now()
);

create table system_events (
  id bigint generated always as identity primary key,
  severity text check (severity in ('info','warn','error','critical')),
  component text,
  message text,
  detail jsonb,
  created_at timestamptz default now()
);

create table quota_ledger (
  id bigint generated always as identity primary key,
  date date not null,
  api text default 'youtube_data',
  units_used int default 0,
  unique (date, api)
);
