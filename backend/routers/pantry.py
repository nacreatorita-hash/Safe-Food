from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException

from lib.dates import today_iso
from models.schemas import Notification, PantryItem, PantryItemCreate
from repositories.notifications import insert as insert_notification
from repositories.pantry import delete_item, insert_item, list_items
from services.ingestion.notification_matcher import best_match, status_for

router = APIRouter()


def _clean(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k != "_id"}


def _is_expired(value: str | None) -> bool:
    if not value:
        return False
    try:
        return date.fromisoformat(value) < date.fromisoformat(today_iso())
    except ValueError:
        return False


async def _decorate(doc: dict[str, Any]) -> PantryItem:
    confidence, label, recall = await best_match(doc)
    status = status_for(confidence)
    if status == "ok" and _is_expired(doc.get("expiration_date")):
        status, label = "scaduto", "Prodotto scaduto: verifica prima del consumo"
    item = PantryItem(**_clean(doc))
    item.status = status  # type: ignore[assignment]
    item.status_label = label
    item.match_confidence = round(confidence, 2)
    item.matched_recall_id = recall.get("id") if recall and confidence >= 0.5 else None
    item.matched_recall_title = recall.get("title") if recall and confidence >= 0.5 else None
    return item


@router.get("/pantry", response_model=list[PantryItem])
async def list_pantry():
    docs = await list_items()
    return [await _decorate(d) for d in docs]


@router.post("/pantry", response_model=PantryItem, status_code=201)
async def add_pantry_item(payload: PantryItemCreate):
    item = PantryItem(**payload.model_dump())
    await insert_item(item.model_dump())
    decorated = await _decorate(item.model_dump())
    if decorated.match_confidence >= 0.5:
        strong = decorated.match_confidence >= 0.95
        await insert_notification(
            Notification(
                type="lotto_corrispondente" if strong else "richiamo_prodotto",
                title="ATTENZIONE: il lotto salvato risulta coinvolto in un richiamo" if strong
                else "Un prodotto salvato potrebbe essere coinvolto in un richiamo",
                body=f"{decorated.name} — {decorated.status_label}",
                recall_id=decorated.matched_recall_id,
            ).model_dump()
        )
    return decorated


@router.delete("/pantry/{item_id}", status_code=204)
async def delete_pantry_item(item_id: str):
    if not await delete_item(item_id):
        raise HTTPException(status_code=404, detail="Prodotto non trovato in dispensa")
    return None
