-- Food Alert Italia: canonical Supabase/Postgres schema.
-- Apply this file in Supabase SQL Editor or with a migration runner.
-- The backend uses the service connection; RLS prevents accidental public
-- access if a table is ever exposed through Supabase Data API.

create extension if not exists pgcrypto;

create table if not exists status_checks (
  id text primary key default gen_random_uuid()::text,
  client_name text not null,
  timestamp timestamptz not null default now()
);

create table if not exists recalls (
  id text primary key default gen_random_uuid()::text,
  source text not null,
  source_id text not null,
  source_url text,
  pdf_url text,
  product_url text,
  image_url text,
  title text not null,
  brand text,
  product_name text not null,
  category text,
  ean text,
  risk_type text not null default 'altro',
  severity text not null default 'attenzione',
  risk_description text,
  consumer_advice text,
  osa text,
  producer text,
  plant_mark text,
  plant text,
  package_size text,
  expiration_date text,
  document_date text,
  lots jsonb not null default '[]'::jsonb,
  is_seafood boolean not null default false,
  fao_area_code text,
  scientific_name text,
  production_method text,
  published_at timestamptz not null,
  content_hash text not null,
  verified boolean not null default false,
  is_demo boolean not null default false,
  field_confidence jsonb not null default '{}'::jsonb,
  official_fields jsonb not null default '{}'::jsonb,
  retrieved_at timestamptz not null default now(),
  unique (source, source_id)
);

create index if not exists recalls_published_idx on recalls (published_at desc);
create index if not exists recalls_risk_published_idx on recalls (risk_type, published_at desc);
create index if not exists recalls_ean_idx on recalls (ean);
create index if not exists recalls_brand_idx on recalls (brand);
create index if not exists recalls_seafood_idx on recalls (is_seafood);
create index if not exists recalls_lots_gin_idx on recalls using gin (lots);

create table if not exists recall_versions (
  version_id text primary key default gen_random_uuid()::text,
  recall_id text not null,
  source text,
  source_id text,
  snapshot jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists pantry_items (
  id text primary key default gen_random_uuid()::text,
  name text not null,
  brand text,
  ean text,
  lot_code text,
  expiration_date text,
  purchase_date text,
  store text,
  created_at timestamptz not null default now()
);
create index if not exists pantry_created_idx on pantry_items (created_at desc);
create index if not exists pantry_ean_idx on pantry_items (ean);

create table if not exists notifications (
  id text primary key default gen_random_uuid()::text,
  type text not null,
  title text not null,
  body text not null,
  recall_id text references recalls(id) on delete set null,
  read boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists notifications_created_idx on notifications (created_at desc);

create table if not exists fao_areas (
  id text primary key default gen_random_uuid()::text,
  code text not null unique,
  name_it text not null,
  name_en text not null,
  parent_code text,
  level integer not null default 1,
  level_label text not null default 'Area principale',
  ocean text,
  description text,
  common_species jsonb not null default '[]'::jsonb,
  centroid_lat double precision,
  centroid_lon double precision,
  source_name text not null default 'FAO Major Fishing Areas',
  source_url text not null default 'https://www.fao.org/fishery/en/area/search',
  source_record_id text,
  geometry jsonb,
  geometry_overview jsonb,
  retrieved_at timestamptz,
  updated_at timestamptz not null default now()
);
create index if not exists fao_parent_idx on fao_areas (parent_code);
create index if not exists fao_level_idx on fao_areas (level);

create table if not exists environment_measurements (
  id text primary key default gen_random_uuid()::text,
  fao_area_code text not null,
  source text not null,
  source_url text not null,
  parameter text not null,
  label_it text not null,
  value double precision,
  unit text not null,
  reference_value double precision,
  reference_note text,
  sample_type text not null,
  species text,
  depth double precision,
  latitude double precision,
  longitude double precision,
  measurement_date text,
  quality_flag text not null default 'non_validato',
  is_demo boolean not null default false,
  retrieved_at timestamptz not null default now()
);
create index if not exists environment_area_sample_idx on environment_measurements (fao_area_code, sample_type);

create table if not exists data_sources (
  id text primary key default gen_random_uuid()::text,
  name text not null,
  url text not null,
  source_type text not null,
  schedule text not null,
  active boolean not null default true,
  last_sync_at timestamptz,
  last_successful_sync_at timestamptz,
  last_error text,
  record_count integer not null default 0,
  pending_count integer not null default 0,
  last_recheck_at timestamptz,
  pending_entries jsonb not null default '[]'::jsonb
);

-- No table is public by default. The FastAPI service connects with its server
-- credential and is the only application data access layer in this task.
alter table status_checks enable row level security;
alter table recalls enable row level security;
alter table recall_versions enable row level security;
alter table pantry_items enable row level security;
alter table notifications enable row level security;
alter table fao_areas enable row level security;
alter table environment_measurements enable row level security;
alter table data_sources enable row level security;
