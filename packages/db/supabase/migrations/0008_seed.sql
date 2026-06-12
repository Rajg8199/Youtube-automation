-- 0008_seed.sql
-- Seed data: research sources + default autonomy gates (all manual per guardrails).

-- ---- RSS sources (tech/phone news) ----
insert into sources (name, type, url, config, trust_score) values
  ('GSMArena',          'rss', 'https://www.gsmarena.com/rss-news-reviews.php3', '{"region":"global"}', 0.80),
  ('91mobiles',         'rss', 'https://www.91mobiles.com/hub/feed/',            '{"region":"india"}',  0.70),
  ('Android Authority', 'rss', 'https://www.androidauthority.com/feed/',          '{"region":"global"}', 0.75),
  ('XDA Developers',    'rss', 'https://www.xda-developers.com/feed/',            '{"region":"global"}', 0.75),
  ('MySmartPrice',      'rss', 'https://www.mysmartprice.com/gear/feed/',         '{"region":"india"}',  0.65),
  ('Gadgets360',        'rss', 'https://www.gadgets360.com/rss/news',             '{"region":"india"}',  0.70);

-- ---- Reddit sources (JSON listings) ----
insert into sources (name, type, url, config, trust_score) values
  ('r/Android',      'reddit', 'https://www.reddit.com/r/Android/new.json',      '{"subreddit":"Android"}',      0.55),
  ('r/PhoneIndia',   'reddit', 'https://www.reddit.com/r/PhoneIndia/new.json',   '{"subreddit":"PhoneIndia"}',   0.55),
  ('r/IndianGaming', 'reddit', 'https://www.reddit.com/r/IndianGaming/new.json', '{"subreddit":"IndianGaming"}', 0.50);

-- ---- Autonomy gates: default to manual (guardrail #1) ----
insert into autonomy_settings (gate, mode) values
  ('topic_selection', 'manual'),
  ('script',          'manual'),
  ('publish',         'manual');
