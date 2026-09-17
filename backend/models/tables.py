"""SQLAlchemy Core table definitions matching the Supabase migration."""

from sqlalchemy import Boolean, DateTime, Float, Integer, MetaData, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Table

metadata = MetaData()

status_checks = Table(
    "status_checks", metadata,
    Column("id", Text, primary_key=True), Column("client_name", Text, nullable=False),
    Column("timestamp", DateTime(timezone=True), nullable=False),
)

recalls = Table(
    "recalls", metadata,
    Column("id", Text, primary_key=True), Column("source", Text, nullable=False), Column("source_id", Text, nullable=False),
    Column("source_url", Text), Column("pdf_url", Text), Column("product_url", Text), Column("image_url", Text),
    Column("title", Text, nullable=False), Column("brand", Text), Column("product_name", Text, nullable=False),
    Column("category", Text), Column("ean", Text), Column("risk_type", Text, nullable=False),
    Column("severity", Text, nullable=False), Column("risk_description", Text), Column("consumer_advice", Text),
    Column("osa", Text), Column("producer", Text), Column("plant_mark", Text), Column("plant", Text),
    Column("package_size", Text), Column("expiration_date", Text), Column("document_date", Text),
    Column("lots", JSONB, nullable=False), Column("is_seafood", Boolean, nullable=False), Column("fao_area_code", Text),
    Column("scientific_name", Text), Column("production_method", Text), Column("published_at", DateTime(timezone=True), nullable=False),
    Column("content_hash", Text, nullable=False), Column("verified", Boolean, nullable=False),
    Column("is_demo", Boolean, nullable=False), Column("field_confidence", JSONB, nullable=False),
    Column("official_fields", JSONB, nullable=False),
    Column("retrieved_at", DateTime(timezone=True), nullable=False),
)

recall_versions = Table(
    "recall_versions", metadata,
    Column("version_id", Text, primary_key=True), Column("recall_id", Text, nullable=False),
    Column("source", Text), Column("source_id", Text), Column("snapshot", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

pantry_items = Table(
    "pantry_items", metadata,
    Column("id", Text, primary_key=True), Column("name", Text, nullable=False), Column("brand", Text),
    Column("ean", Text), Column("lot_code", Text), Column("expiration_date", Text), Column("purchase_date", Text),
    Column("store", Text), Column("created_at", DateTime(timezone=True), nullable=False),
)

notifications = Table(
    "notifications", metadata,
    Column("id", Text, primary_key=True), Column("type", Text, nullable=False), Column("title", Text, nullable=False),
    Column("body", Text, nullable=False), Column("recall_id", Text), Column("read", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

fao_areas = Table(
    "fao_areas", metadata,
    Column("id", Text, primary_key=True, server_default=text("gen_random_uuid()::text")), Column("code", Text, nullable=False), Column("name_it", Text, nullable=False),
    Column("name_en", Text, nullable=False), Column("parent_code", Text), Column("level", Integer, nullable=False),
    Column("level_label", Text, nullable=False), Column("ocean", Text), Column("description", Text),
    Column("common_species", JSONB, nullable=False), Column("centroid_lat", Float), Column("centroid_lon", Float),
    Column("source_name", Text, nullable=False), Column("source_url", Text, nullable=False), Column("source_record_id", Text),
    Column("geometry", JSONB), Column("geometry_overview", JSONB), Column("retrieved_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

environment_measurements = Table(
    "environment_measurements", metadata,
    Column("id", Text, primary_key=True), Column("fao_area_code", Text, nullable=False), Column("source", Text, nullable=False),
    Column("source_url", Text, nullable=False), Column("parameter", Text, nullable=False), Column("label_it", Text, nullable=False),
    Column("value", Float), Column("unit", Text, nullable=False), Column("reference_value", Float), Column("reference_note", Text),
    Column("sample_type", Text, nullable=False), Column("species", Text), Column("depth", Float), Column("latitude", Float),
    Column("longitude", Float), Column("measurement_date", Text), Column("quality_flag", Text, nullable=False),
    Column("is_demo", Boolean, nullable=False), Column("retrieved_at", DateTime(timezone=True), nullable=False),
)

data_sources = Table(
    "data_sources", metadata,
    Column("id", Text, primary_key=True), Column("name", Text, nullable=False), Column("url", Text, nullable=False),
    Column("source_type", Text, nullable=False), Column("schedule", Text, nullable=False), Column("active", Boolean, nullable=False),
    Column("last_sync_at", DateTime(timezone=True)), Column("last_successful_sync_at", DateTime(timezone=True)),
    Column("last_error", Text), Column("record_count", Integer, nullable=False), Column("pending_count", Integer, nullable=False),
    Column("last_recheck_at", DateTime(timezone=True)), Column("pending_entries", JSONB, nullable=False),
)

TABLES = {
    "status_checks": status_checks,
    "recalls": recalls,
    "recall_versions": recall_versions,
    "pantry_items": pantry_items,
    "notifications": notifications,
    "fao_areas": fao_areas,
    "environment_measurements": environment_measurements,
    "data_sources": data_sources,
}
