"""Pydantic v2 models. Each has a hand-written TS mirror in frontend/src/types/api.ts."""

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

RiskType = Literal["microbiologico", "chimico", "allergeni", "fisico", "etichettatura", "altro"]
Severity = Literal["grave", "attenzione", "informativo"]


def _uid() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class RecallLot(BaseModel):
    lot_code: str
    expiration_date: Optional[str] = None
    notes: Optional[str] = None


class Recall(BaseModel):
    id: str = Field(default_factory=_uid)
    source: str
    source_id: str
    source_url: Optional[str] = None
    pdf_url: Optional[str] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    title: str
    brand: Optional[str] = None
    product_name: str
    category: Optional[str] = None
    ean: Optional[str] = None
    risk_type: RiskType = "altro"
    severity: Severity = "attenzione"
    risk_description: Optional[str] = None
    consumer_advice: Optional[str] = None
    osa: Optional[str] = None
    producer: Optional[str] = None
    plant_mark: Optional[str] = None
    plant: Optional[str] = None
    package_size: Optional[str] = None
    expiration_date: Optional[str] = None
    document_date: Optional[str] = None
    lots: list[RecallLot] = Field(default_factory=list)
    is_seafood: bool = False
    fao_area_code: Optional[str] = None
    scientific_name: Optional[str] = None
    production_method: Optional[str] = None
    published_at: datetime
    content_hash: str
    verified: bool = False
    is_demo: bool = False
    field_confidence: dict[str, float] = Field(default_factory=dict)
    official_fields: dict[str, str] = Field(default_factory=dict)
    retrieved_at: datetime = Field(default_factory=now_utc)


class RecallStats(BaseModel):
    total: int
    last_30_days: int
    microbiologico: int
    allergeni: int
    chimico: int
    fisico: int
    seafood: int


class PantryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    brand: Optional[str] = Field(default=None, max_length=100)
    ean: Optional[str] = Field(default=None, max_length=32)
    lot_code: Optional[str] = Field(default=None, max_length=100)
    expiration_date: Optional[str] = Field(default=None, max_length=32)
    purchase_date: Optional[str] = Field(default=None, max_length=32)
    store: Optional[str] = Field(default=None, max_length=100)


class PantryItem(BaseModel):
    id: str = Field(default_factory=_uid)
    name: str
    brand: Optional[str] = None
    ean: Optional[str] = None
    lot_code: Optional[str] = None
    expiration_date: Optional[str] = None
    purchase_date: Optional[str] = None
    store: Optional[str] = None
    created_at: datetime = Field(default_factory=now_utc)
    # computed at read time by the matching service
    status: Literal["ok", "controlla_lotto", "richiamato", "scaduto"] = "ok"
    status_label: str = "Nessun richiamo corrispondente"
    match_confidence: float = 0.0
    matched_recall_id: Optional[str] = None
    matched_recall_title: Optional[str] = None


class FaoArea(BaseModel):
    id: str = Field(default_factory=_uid)
    code: str
    name_it: str
    name_en: str
    parent_code: Optional[str] = None
    level: int = 1
    level_label: str = "Area principale"
    ocean: Optional[str] = None
    description: Optional[str] = None
    common_species: list[str] = Field(default_factory=list)
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    source_name: str = "FAO Major Fishing Areas"
    source_url: str = "https://www.fao.org/fishery/en/area/search"
    source_record_id: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=now_utc)


class FaoGeometry(BaseModel):
    code: str
    geometry: dict
    source_name: str
    source_url: str


class EnvironmentMeasurement(BaseModel):
    id: str = Field(default_factory=_uid)
    fao_area_code: str
    source: str
    source_url: str
    parameter: str
    label_it: str
    value: Optional[float] = None
    unit: str
    reference_value: Optional[float] = None
    reference_note: Optional[str] = None
    sample_type: Literal["water", "sediment", "biota"]
    species: Optional[str] = None
    depth: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    measurement_date: Optional[str] = None
    quality_flag: str = "non_validato"
    is_demo: bool = False
    retrieved_at: datetime = Field(default_factory=now_utc)


class EnvironmentSummary(BaseModel):
    fao_area_code: str
    water: list[EnvironmentMeasurement] = Field(default_factory=list)
    sediment: list[EnvironmentMeasurement] = Field(default_factory=list)
    biota: list[EnvironmentMeasurement] = Field(default_factory=list)
    last_updated: Optional[datetime] = None
    sources: list[str] = Field(default_factory=list)
    note: str


class Notification(BaseModel):
    id: str = Field(default_factory=_uid)
    type: Literal["richiamo_prodotto", "lotto_corrispondente", "marca_seguita", "zona_fao", "ambientale"]
    title: str
    body: str
    recall_id: Optional[str] = None
    read: bool = False
    created_at: datetime = Field(default_factory=now_utc)


class DataSource(BaseModel):
    id: str = Field(default_factory=_uid)
    name: str
    url: str
    source_type: str
    schedule: str
    active: bool = True
    last_sync_at: Optional[datetime] = None
    last_successful_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    record_count: int = 0
    pending_count: int = 0
    last_recheck_at: Optional[datetime] = None


class SyncResult(BaseModel):
    source_id: str
    ok: bool
    message: str
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0
