-- 0001_extensions.sql
-- Required Postgres extensions.
create extension if not exists pgcrypto;   -- gen_random_uuid()
create extension if not exists vector;     -- pgvector (embeddings + HNSW)
