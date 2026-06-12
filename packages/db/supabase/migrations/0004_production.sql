-- 0004_production.sql
-- Production layer: media assets, scene plans, thumbnails, SEO metadata.

create table media_assets (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid references content_items(id),
  kind text check (kind in ('voiceover','broll','press_render','chart','music','sfx','render_segment','final_video','thumbnail','subtitle')),
  storage_path text not null,              -- Supabase Storage path
  duration_sec numeric,
  meta jsonb default '{}',                 -- provider, license, source_url, scene index
  cost_usd numeric default 0,
  created_at timestamptz default now()
);

create table scene_plans (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid references content_items(id) on delete cascade,
  scenes jsonb not null,                   -- [{idx, script_segment, template, assets[], duration, remotion_props}]
  created_at timestamptz default now()
);

create table thumbnails (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid references content_items(id) on delete cascade,
  variant text not null,                   -- 'A','B','C'
  asset_id uuid references media_assets(id),
  concept text,                            -- emotion, text overlay, composition
  is_selected boolean default false,
  ab_test_result jsonb,                    -- from YouTube Test & Compare
  created_at timestamptz default now()
);

create table seo_metadata (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid references content_items(id) on delete cascade,
  title text not null,                     -- <=100 chars, keyword-front-loaded
  title_variants text[],
  description text not null,               -- with timestamps + affiliate links
  tags text[],
  hashtags text[],
  category_id int default 28,              -- Science & Tech
  affiliate_links jsonb default '[]',      -- [{device, amazon_url, flipkart_url}]
  chapters jsonb default '[]',
  created_at timestamptz default now()
);
