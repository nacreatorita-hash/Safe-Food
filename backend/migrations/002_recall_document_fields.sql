-- Add fields extracted from the official Ministero recall document.
-- Safe to run against the already-provisioned Supabase project.
alter table recalls add column if not exists osa text;
alter table recalls add column if not exists plant_mark text;
alter table recalls add column if not exists document_date text;
alter table recalls add column if not exists official_fields jsonb not null default '{}'::jsonb;
