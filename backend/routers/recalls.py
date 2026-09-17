from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from models.schemas import Recall, RecallStats
from repositories.recalls import get_recall as repository_get_recall
from repositories.recalls import list_brands, list_recalls as repository_list_recalls
from repositories.recalls import recall_stats as repository_recall_stats

router = APIRouter()


@router.get("/recalls", response_model=list[Recall])
async def list_recalls(
    q: Optional[str] = Query(None, max_length=100),
    risk_type: Optional[str] = Query(None, max_length=40),
    brand: Optional[str] = Query(None, max_length=100),
    category: Optional[str] = Query(None, max_length=100),
    seafood: Optional[bool] = None,
    sort: str = "recent",
    limit: int = Query(50, ge=1, le=200),
):
    query: dict[str, Any] = {}
    if q:
        query["q"] = q
    if risk_type:
        query["risk_type"] = risk_type
    if brand:
        query["brand"] = brand
    if category:
        query["category"] = category
    if seafood is not None:
        query["is_seafood"] = seafood

    docs = await repository_list_recalls(query, sort, limit)
    return [Recall(**doc) for doc in docs]


@router.get("/recalls/stats", response_model=RecallStats)
async def recall_stats():
    return RecallStats(**await repository_recall_stats())


@router.get("/recalls/brands", response_model=list[str])
async def recall_brands():
    return await list_brands()


@router.get("/recalls/{recall_id}", response_model=Recall)
async def get_recall(recall_id: str):
    doc = await repository_get_recall(recall_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Richiamo non trovato")
    return Recall(**doc)
