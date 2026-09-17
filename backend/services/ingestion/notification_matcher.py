"""Match recalls against saved pantry items and grade the confidence of each match.

Priority: 1) EAN + lotto  2) EAN  3) marca + prodotto + lotto  4) marca + prodotto.
A "certain" claim is only made when the lot code matches.
"""

from typing import Any, Optional

from models.schemas import Notification
from repositories.notifications import insert as insert_notification
from repositories.pantry import all_items
from repositories.recalls import candidate_recalls


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _lots(recall: dict[str, Any]) -> set[str]:
    return {_norm(lot.get("lot_code")) for lot in recall.get("lots", []) if lot.get("lot_code")}


def match(item: dict[str, Any], recall: dict[str, Any]) -> tuple[float, str]:
    """Return (confidence, human label) for a single pantry-item ↔ recall pair."""
    item_ean, recall_ean = _norm(item.get("ean")), _norm(recall.get("ean"))
    item_lot = _norm(item.get("lot_code"))
    lots = _lots(recall)
    ean_hit = bool(item_ean) and item_ean == recall_ean
    lot_hit = bool(item_lot) and item_lot in lots

    if ean_hit and lot_hit:
        return 1.0, "Il lotto che hai registrato risulta coinvolto nel richiamo."
    if ean_hit:
        return 0.75, "Prodotto corrispondente per EAN: verifica il lotto sulla confezione."

    name_hit = bool(_norm(item.get("name"))) and _norm(item.get("name")) in _norm(recall.get("product_name"))
    brand_hit = bool(_norm(item.get("brand"))) and _norm(item.get("brand")) == _norm(recall.get("brand"))
    if brand_hit and name_hit and lot_hit:
        return 0.95, "Il lotto che hai registrato risulta coinvolto nel richiamo."
    if brand_hit and name_hit:
        return 0.6, "Possibile corrispondenza per marca e prodotto: verifica il lotto."
    if brand_hit and lot_hit:
        return 0.7, "Marca e lotto corrispondono: verifica il prodotto sulla confezione."
    return 0.0, "Nessun richiamo corrispondente"


def status_for(confidence: float) -> str:
    if confidence >= 0.95:
        return "richiamato"
    if confidence >= 0.5:
        return "controlla_lotto"
    return "ok"


async def best_match(item: dict[str, Any]) -> tuple[float, str, Optional[dict[str, Any]]]:
    candidates = await candidate_recalls(item)
    if not candidates:
        return 0.0, "Nessun richiamo corrispondente", None

    best: tuple[float, str, Optional[dict[str, Any]]] = (0.0, "Nessun richiamo corrispondente", None)
    for recall in candidates:
        confidence, label = match(item, recall)
        if confidence > best[0]:
            best = (confidence, label, recall)
    return best


async def notify_for_new_recall(recall: dict[str, Any]) -> int:
    """Create notifications for pantry items touched by a freshly ingested recall."""
    created = 0
    for item in await all_items():
        confidence, label = match(item, recall)
        if confidence < 0.5:
            continue
        strong = confidence >= 0.95
        note = Notification(
            type="lotto_corrispondente" if strong else "richiamo_prodotto",
            title=("ATTENZIONE: il lotto salvato risulta coinvolto" if strong
                   else "Un prodotto della tua dispensa potrebbe essere coinvolto"),
            body=f"{item.get('name')} — {label}",
            recall_id=recall.get("id"),
        )
        await insert_notification(note.model_dump())
        created += 1
    return created
