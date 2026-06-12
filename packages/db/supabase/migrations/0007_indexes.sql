-- 0007_indexes.sql
-- Indexes on FK columns, hot status/date columns, and HNSW on every vector column.

-- ---- Foreign-key indexes ----
create index idx_raw_signals_source_id        on raw_signals(source_id);
create index idx_topic_scores_topic_id        on topic_scores(topic_id);
create index idx_content_items_topic_id       on content_items(topic_id);
create index idx_content_items_parent_id      on content_items(parent_id);
create index idx_pipeline_events_item_id      on pipeline_events(content_item_id);
create index idx_research_briefs_item_id      on research_briefs(content_item_id);
create index idx_scripts_item_id              on scripts(content_item_id);
create index idx_script_qa_reports_script_id  on script_qa_reports(script_id);
create index idx_media_assets_item_id         on media_assets(content_item_id);
create index idx_scene_plans_item_id          on scene_plans(content_item_id);
create index idx_thumbnails_item_id           on thumbnails(content_item_id);
create index idx_thumbnails_asset_id          on thumbnails(asset_id);
create index idx_seo_metadata_item_id         on seo_metadata(content_item_id);
create index idx_publish_jobs_item_id         on publish_jobs(content_item_id);
create index idx_youtube_videos_item_id       on youtube_videos(content_item_id);
create index idx_approvals_item_id            on approvals(content_item_id);
create index idx_competitor_videos_comp_id    on competitor_videos(competitor_id);

-- ---- Hot status / date columns ----
create index idx_content_items_status         on content_items(status);
create index idx_topics_status                on topics(status);
create index idx_video_metrics_daily_date     on video_metrics_daily(date);

-- ---- HNSW indexes on vector columns (cosine distance) ----
create index idx_raw_signals_embedding        on raw_signals        using hnsw (embedding vector_cosine_ops);
create index idx_topics_embedding             on topics             using hnsw (embedding vector_cosine_ops);
create index idx_youtube_videos_topic_emb     on youtube_videos     using hnsw (topic_embedding vector_cosine_ops);
create index idx_youtube_videos_hook_emb      on youtube_videos     using hnsw (hook_embedding vector_cosine_ops);
create index idx_competitor_videos_topic_emb  on competitor_videos  using hnsw (topic_embedding vector_cosine_ops);
