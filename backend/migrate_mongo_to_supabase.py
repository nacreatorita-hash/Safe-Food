"""One-time, non-destructive MongoDB -> Supabase migration.

The application no longer imports Motor/MongoDB. This utility is kept only for
moving an existing Mongo dataset into the new Postgres schema. It defaults to
dry-run; pass ``--apply`` only after checking the source and target settings.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from pymongo import MongoClient
from psycopg.types.json import Jsonb

load_dotenv(Path(__file__).parent / ".env")


def _pg_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if value.startswith("postgresql+asyncpg://"):
        return "postgresql://" + value.removeprefix("postgresql+asyncpg://")
    if value.startswith("postgres://"):
        return "postgresql://" + value.removeprefix("postgres://")
    return value


def _value(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return value


def _json(value: Any, default: Any) -> Jsonb:
    return Jsonb(value if value is not None else default)


def _recall_args(doc: dict[str, Any]) -> tuple[Any, ...]:
    return (
        doc.get("id"), doc.get("source"), doc.get("source_id"), doc.get("source_url"), doc.get("pdf_url"),
        doc.get("product_url"), doc.get("image_url"), doc.get("title", ""), doc.get("brand"), doc.get("product_name", ""),
        doc.get("category"), doc.get("ean"), doc.get("risk_type", "altro"), doc.get("severity", "attenzione"),
        doc.get("risk_description"), doc.get("consumer_advice"), doc.get("producer"), doc.get("plant"),
        doc.get("package_size"), doc.get("expiration_date"), _json(doc.get("lots"), []),
        _value(doc.get("is_seafood"), False), doc.get("fao_area_code"), doc.get("scientific_name"),
        doc.get("production_method"), _value(doc.get("published_at"), datetime.now(timezone.utc)),
        doc.get("content_hash", ""), _value(doc.get("verified"), False), _value(doc.get("is_demo"), False),
        _json(doc.get("field_confidence"), {}), _value(doc.get("retrieved_at"), datetime.now(timezone.utc)),
    )


def _migrate_collection(mongo_db, cur, collection: str, apply: bool) -> int:
    docs = list(mongo_db[collection].find({}))
    if not apply:
        return len(docs)

    if collection == "recalls":
        sql = """
            insert into recalls (id,source,source_id,source_url,pdf_url,product_url,image_url,title,brand,product_name,
            category,ean,risk_type,severity,risk_description,consumer_advice,producer,plant,package_size,expiration_date,
            lots,is_seafood,fao_area_code,scientific_name,production_method,published_at,content_hash,verified,is_demo,
            field_confidence,retrieved_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            on conflict (source,source_id) do update set
            source_url=excluded.source_url,pdf_url=excluded.pdf_url,product_url=excluded.product_url,image_url=excluded.image_url,
            title=excluded.title,brand=excluded.brand,product_name=excluded.product_name,category=excluded.category,ean=excluded.ean,
            risk_type=excluded.risk_type,severity=excluded.severity,risk_description=excluded.risk_description,
            consumer_advice=excluded.consumer_advice,producer=excluded.producer,plant=excluded.plant,package_size=excluded.package_size,
            expiration_date=excluded.expiration_date,lots=excluded.lots,is_seafood=excluded.is_seafood,fao_area_code=excluded.fao_area_code,
            scientific_name=excluded.scientific_name,production_method=excluded.production_method,published_at=excluded.published_at,
            content_hash=excluded.content_hash,verified=excluded.verified,is_demo=excluded.is_demo,
            field_confidence=excluded.field_confidence,retrieved_at=excluded.retrieved_at
        """
        cur.executemany(sql, [_recall_args(doc) for doc in docs])
    elif collection == "recall_versions":
        cur.executemany(
            "insert into recall_versions (version_id,recall_id,source,source_id,snapshot,created_at) values (%s,%s,%s,%s,%s,%s) on conflict (version_id) do nothing",
            [(str(doc.get("version_id") or doc.get("id")), str(doc.get("recall_id") or doc.get("id") or ""), doc.get("source"),
              doc.get("source_id"), _json({key: value for key, value in doc.items() if key != "_id"}, {}),
              _value(doc.get("created_at"), datetime.now(timezone.utc))) for doc in docs],
        )
    elif collection == "pantry_items":
        cur.executemany(
            "insert into pantry_items (id,name,brand,ean,lot_code,expiration_date,purchase_date,store,created_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (id) do nothing",
            [(doc.get("id"), doc.get("name", ""), doc.get("brand"), doc.get("ean"), doc.get("lot_code"), doc.get("expiration_date"),
              doc.get("purchase_date"), doc.get("store"), _value(doc.get("created_at"), datetime.now(timezone.utc))) for doc in docs],
        )
    elif collection == "notifications":
        cur.executemany(
            "insert into notifications (id,type,title,body,recall_id,read,created_at) values (%s,%s,%s,%s,%s,%s,%s) on conflict (id) do nothing",
            [(doc.get("id"), doc.get("type", "richiamo_prodotto"), doc.get("title", ""), doc.get("body", ""), doc.get("recall_id"),
              doc.get("read", False), _value(doc.get("created_at"), datetime.now(timezone.utc))) for doc in docs],
        )
    elif collection == "fao_areas":
        cur.executemany(
            """insert into fao_areas (id,code,name_it,name_en,parent_code,level,level_label,ocean,description,common_species,
            centroid_lat,centroid_lon,source_name,source_url,source_record_id,geometry,geometry_overview,retrieved_at,updated_at)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            on conflict (code) do update set name_it=excluded.name_it,name_en=excluded.name_en,parent_code=excluded.parent_code,
            level=excluded.level,level_label=excluded.level_label,ocean=excluded.ocean,description=excluded.description,
            common_species=excluded.common_species,centroid_lat=excluded.centroid_lat,centroid_lon=excluded.centroid_lon,
            source_name=excluded.source_name,source_url=excluded.source_url,source_record_id=excluded.source_record_id,
            geometry=excluded.geometry,geometry_overview=excluded.geometry_overview,retrieved_at=excluded.retrieved_at,updated_at=excluded.updated_at""",
            [(doc.get("id"), doc.get("code"), doc.get("name_it", ""), doc.get("name_en", ""), doc.get("parent_code"), doc.get("level", 1),
              doc.get("level_label", "Area principale"), doc.get("ocean"), doc.get("description"), _json(doc.get("common_species"), []),
              doc.get("centroid_lat"), doc.get("centroid_lon"), doc.get("source_name", "FAO Major Fishing Areas"), doc.get("source_url", ""),
              doc.get("source_record_id"), _json(doc.get("geometry"), None), _json(doc.get("geometry_overview"), None),
              _value(doc.get("retrieved_at")), _value(doc.get("updated_at"), datetime.now(timezone.utc))) for doc in docs],
        )
    elif collection == "environment_measurements":
        fields = ("id", "fao_area_code", "source", "source_url", "parameter", "label_it", "value", "unit", "reference_value",
                  "reference_note", "sample_type", "species", "depth", "latitude", "longitude", "measurement_date", "quality_flag", "is_demo", "retrieved_at")
        cur.executemany(
            "insert into environment_measurements (" + ",".join(fields) + ") values (" + ",".join(["%s"] * len(fields)) + ") on conflict (id) do nothing",
            [tuple(_value(doc.get(field), False if field == "is_demo" else ("non_validato" if field == "quality_flag" else datetime.now(timezone.utc) if field == "retrieved_at" else None))) for doc in docs],
        )
    elif collection == "data_sources":
        cur.executemany(
            """insert into data_sources (id,name,url,source_type,schedule,active,last_sync_at,last_successful_sync_at,last_error,
            record_count,pending_count,last_recheck_at,pending_entries) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            on conflict (id) do update set name=excluded.name,url=excluded.url,source_type=excluded.source_type,schedule=excluded.schedule,
            active=excluded.active,last_sync_at=excluded.last_sync_at,last_successful_sync_at=excluded.last_successful_sync_at,
            last_error=excluded.last_error,record_count=excluded.record_count,pending_count=excluded.pending_count,
            last_recheck_at=excluded.last_recheck_at,pending_entries=excluded.pending_entries""",
            [(doc.get("id"), doc.get("name", ""), doc.get("url", ""), doc.get("source_type", ""), doc.get("schedule", ""), doc.get("active", True),
              _value(doc.get("last_sync_at")), _value(doc.get("last_successful_sync_at")), doc.get("last_error"), doc.get("record_count", 0),
              doc.get("pending_count", 0), _value(doc.get("last_recheck_at")), _json(doc.get("pending_entries"), [])) for doc in docs],
        )
    elif collection == "status_checks":
        cur.executemany(
            "insert into status_checks (id,client_name,timestamp) values (%s,%s,%s) on conflict (id) do nothing",
            [(doc.get("id"), doc.get("client_name", ""), _value(doc.get("timestamp"), datetime.now(timezone.utc))) for doc in docs],
        )
    return len(docs)


def main(*, apply: bool) -> None:
    mongo_url = os.environ.get("MONGO_URL", "").strip()
    postgres_url = _pg_url()
    if not mongo_url or not postgres_url:
        raise RuntimeError("MONGO_URL e DATABASE_URL devono essere configurati per la migrazione")
    collections = ["status_checks", "recalls", "recall_versions", "pantry_items", "notifications", "fao_areas",
                   "environment_measurements", "data_sources"]
    with MongoClient(mongo_url, serverSelectionTimeoutMS=5000) as mongo, psycopg.connect(postgres_url) as connection:
        mongo_db = mongo[os.environ.get("MONGO_DB_NAME", os.environ.get("DB_NAME", "food_alert_italia"))]
        with connection.cursor() as cur:
            totals = {collection: _migrate_collection(mongo_db, cur, collection, apply) for collection in collections}
        if apply:
            connection.commit()
        print(("Migratione applicata" if apply else "Dry-run") + ": " + ", ".join(f"{key}={value}" for key, value in totals.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migra dati MongoDB nello schema Supabase/Postgres senza cancellare la sorgente.")
    parser.add_argument("--apply", action="store_true", help="scrive nel database Supabase; senza flag esegue solo conteggio")
    args = parser.parse_args()
    main(apply=args.apply)
