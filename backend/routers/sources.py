"""Public, read-only data-source status used by the methodology page."""

from fastapi import APIRouter

from models.schemas import DataSource
from repositories.sources import list_sources

router = APIRouter()


@router.get("/sources", response_model=list[DataSource])
async def list_public_sources():
    docs = await list_sources()
    return [DataSource(**doc) for doc in docs]
