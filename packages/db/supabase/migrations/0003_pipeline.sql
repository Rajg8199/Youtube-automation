-- 0003_pipeline.sql
-- Content pipeline: the central state machine + research briefs, scripts, QA.

create table content_items (
  id uuid primary key default gen_random_uuid(),
  topic_id uuid references topics(id),
  format text not null check (format in ('long','short')),
  parent_id uuid references content_items(id),  -- shorts derived from a long video
  working_title text not null,
  angle text,                              -- the unique take/hook
  status text not null default 'idea' check (status in (
    'idea','researched','scripting','script_qa','qa_failed','script_approved',
    'voiceover','assembly','thumbnail','metadata','ready_for_review',
    'approved','scheduled','publishing','published','analyzing','archived',
    'rejected','failed')),
  priority int default 50,
  target_publish_at timestamptz,
  failure_reason text,
  autonomy_overrides jsonb default '{}',   -- per-item gate overrides
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table pipeline_events (              -- full audit trail of state transitions
  id bigint generated always as identity primary key,
  content_item_id uuid references content_items(id) on delete cascade,
  from_status text, to_status text,
  actor text,                              -- 'agent:script_writer' | 'human:rj' | 'system'
  detail jsonb default '{}',
  created_at timestamptz default now()
);

create table research_briefs (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid references content_items(id) on delete cascade,
  facts jsonb not null,                    -- [{claim, value, source_url, confidence}]
  spec_table jsonb,                        -- normalized device specs
  price_data jsonb,                        -- {device: {amazon, flipkart, launch_price}}
  competitor_videos jsonb,                 -- what rivals already published on this
  created_at timestamptz default now()
);

create table scripts (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid references content_items(id) on delete cascade,
  version int not null default 1,
  hook text not null,                      -- first 15 seconds, separately stored
  body_markdown text not null,             -- with [SCENE:] markers
  cta text,
  word_count int,
  est_duration_sec int,
  language_mix jsonb,                      -- {hindi_pct, english_pct}
  created_by text default 'agent:script_writer',
  created_at timestamptz default now(),
  unique (content_item_id, version)
);

create table script_qa_reports (
  id uuid primary key default gen_random_uuid(),
  script_id uuid references scripts(id) on delete cascade,
  passed boolean not null,
  claims_checked int,
  claims_failed jsonb default '[]',        -- [{claim, expected, found, source}]
  policy_flags jsonb default '[]',         -- clickbait, medical claims, copyright risk
  readability_notes text,
  created_at timestamptz default now()
);
