"""Admin / ingestion operations: source status and manual sync triggers."""

from fastapi import APIRouter, Depends, HTTPException

from lib.access import require_admin_access
from models.schemas import DataSource, SyncResult
from repositories.sources import get_source, list_sources as repository_list_sources, overview_counts
from services.environment.adapters import ADAPTERS
from services.ingestion.sync import run_source

router = APIRouter()


@router.get("/admin/sources", response_model=list[DataSource], dependencies=[Depends(require_admin_access)])
async def list_sources():
    docs = await repository_list_sources()
    return [DataSource(**doc) for doc in docs]


@router.get("/admin/overview", dependencies=[Depends(require_admin_access)])
async def overview():
    counts = await overview_counts()
    return {
        **counts,
        "environment_adapters": [a.status().__dict__ for a in ADAPTERS],
    }


@router.post("/admin/sync/{source_id}", response_model=SyncResult, dependencies=[Depends(require_admin_access)])
async def trigger_sync(source_id: str):
    source = await get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Fonte dati non trovata")
    return await run_source(source)
