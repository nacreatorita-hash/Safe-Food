from fastapi import APIRouter, HTTPException

from models.schemas import Notification
from repositories.notifications import list_notifications as repository_list_notifications
from repositories.notifications import mark_all_read as repository_mark_all_read
from repositories.notifications import mark_read as repository_mark_read

router = APIRouter()


@router.get("/notifications", response_model=list[Notification])
async def list_notifications():
    return [Notification(**doc) for doc in await repository_list_notifications()]


@router.post("/notifications/{note_id}/read", response_model=Notification)
async def mark_read(note_id: str):
    doc = await repository_mark_read(note_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Notifica non trovata")
    return Notification(**doc)


@router.post("/notifications/read-all", response_model=dict)
async def mark_all_read():
    return {"updated": await repository_mark_all_read()}
