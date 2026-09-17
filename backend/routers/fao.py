from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from models.schemas import EnvironmentMeasurement, EnvironmentSummary, FaoArea, FaoGeometry
from repositories.fao import get_area as repository_get_area
from repositories.fao import get_geometry as repository_get_geometry
from repositories.fao import list_areas as repository_list_areas
from repositories.fao import measurements as repository_measurements
from repositories.fao import overview as repository_overview
from services.environment.adapters import ADAPTERS

router = APIRouter()

DISCLAIMER = (
    "Lo stato ambientale di un'area non determina automaticamente la sicurezza del "
    "singolo alimento. I dati ambientali, la contaminazione nel biota e i richiami "
    "ufficiali sono informazioni distinte."
)
@router.get("/fao/areas", response_model=list[FaoArea])
async def list_areas(parent: str | None = None, level: int | None = Query(None, ge=1, le=5)):
    query: dict[str, Any] = {}
    if parent is not None:
        query["parent_code"] = parent
    if level is not None:
        query["level"] = level
    docs = await repository_list_areas(query)
    return [FaoArea(**d) for d in docs]


@router.get("/fao/areas/{code}", response_model=FaoArea)
async def get_area(code: str):
    doc = await repository_get_area(code)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Zona FAO {code} non trovata")
    return FaoArea(**doc)


@router.get("/fao/areas/{code}/geometry", response_model=FaoGeometry)
async def get_area_geometry(code: str):
    doc = await repository_get_geometry(code)
    if not doc or not doc.get("geometry"):
        raise HTTPException(status_code=404, detail=f"Geometria per la zona FAO {code} non disponibile")
    return FaoGeometry(code=code, geometry=doc["geometry"], source_name=doc["source_name"], source_url=doc["source_url"])


@router.get("/fao/overview")
async def overview_geojson(level: int = Query(1, ge=1, le=3), parent: str | None = None):
    """Lightweight GeoJSON FeatureCollection (thinned outlines) for the map overview layer."""
    query: dict[str, Any] = {"level": level} if parent is None else {"parent_code": parent}
    features = [
        {"type": "Feature", "properties": {"code": d["code"], "name_it": d["name_it"], "level": d["level"]},
         "geometry": d["geometry_overview"]}
        for d in await repository_overview(query)
    ]
    return JSONResponse({"type": "FeatureCollection", "features": features})


@router.get("/environment/summary/{code}", response_model=EnvironmentSummary)
async def environment_summary(code: str):
    docs = await repository_measurements(code)
    measurements = [EnvironmentMeasurement(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]
    last = max((d.get("retrieved_at") for d in docs if d.get("retrieved_at")), default=None)
    if isinstance(last, datetime) and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return EnvironmentSummary(
        fao_area_code=code,
        water=[m for m in measurements if m.sample_type == "water"],
        sediment=[m for m in measurements if m.sample_type == "sediment"],
        biota=[m for m in measurements if m.sample_type == "biota"],
        last_updated=last,
        sources=sorted({m.source for m in measurements}),
        note=DISCLAIMER,
    )


@router.get("/environment/adapters")
async def adapter_status():
    return [a.status().__dict__ for a in ADAPTERS]
