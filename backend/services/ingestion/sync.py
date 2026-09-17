"""Source synchronisation and durable ingestion bookkeeping.

The functions are shared by the admin trigger and the single scheduler
worker. Ministero discovery is queued in ``data_sources.pending_entries`` so a
25-page batch cannot make the remaining archive fall behind permanently.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from models.schemas import RecallLot, SyncResult
from repositories.fao import count_areas, count_measurements, get_area_record as get_fao_area_record
from repositories.fao import list_areas as list_fao_areas
from repositories.fao import replace_measurements, upsert_area
from repositories.recalls import count_for_source, list_source_ids, list_source_ids_needing_enrichment
from repositories.sources import pending_entries, update_source
from services.environment import fao_service
from services.ingestion import ministero_pdf_service as pdf
from services.ingestion import ministero_recall_page_service as pages
from services.ingestion import ministero_rss_service as rss
from services.ingestion import rasff_service
from services.ingestion import recall_normalizer as normalizer
from services.ingestion.duplicate_detector import upsert_recall
from services.ingestion.notification_matcher import notify_for_new_recall
from services.environment.adapters import ADAPTERS

logger = logging.getLogger(__name__)
MINISTERO_SOURCE = "Ministero della Salute"
RASFF_SOURCE = "RASFF — Commissione Europea"
MINISTERO_QUEUE_ID = "src-ministero-rss"
# Keep each hourly cron invocation bounded. The next invocation continues
# from the durable queue, so a large backlog is drained progressively.
MAX_NEW_PAGES_PER_RUN = 5
MAX_RECHECK_PAGES_PER_RUN = 3
MAX_PDFS_PER_RUN = 1


def _seafood(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in ("tonno", "pesce", "salmone", "molluschi", "vongol", "cozze", "gamber",
                                  "calamar", "acciug", "alici", "sgombro", "merluzz", "spada", "polpo", "ittic"))


def _entry_dict(entry: rss.RssEntry) -> dict[str, Any]:
    return {
        "source_id": entry.source_id,
        "title": entry.title,
        "link": entry.link,
        "published": entry.published,
        "summary": entry.summary,
        "feed": entry.feed,
    }


def _entry_from_dict(value: dict[str, Any]) -> rss.RssEntry | None:
    source_id = str(value.get("source_id") or "").strip()
    link = str(value.get("link") or "").strip()
    title = str(value.get("title") or "").strip()
    if not source_id or not link or not title:
        return None
    return rss.RssEntry(
        source_id=source_id,
        title=title,
        link=link,
        published=value.get("published"),
        summary=value.get("summary"),
        feed=str(value.get("feed") or "queue"),
    )


def _merge_entries(pending: list[rss.RssEntry], discovered: list[rss.RssEntry]) -> list[rss.RssEntry]:
    """Keep queue order while letting the newest RSS metadata win."""
    merged: dict[str, rss.RssEntry] = {}
    for entry in [*pending, *discovered]:
        if entry.source_id:
            merged[entry.source_id] = entry
    return list(merged.values())


async def sync_ministero() -> SyncResult:
    entries = await rss.fetch_entries()
    try:
        archive_links = await pages.list_archive_links()
    except Exception as exc:  # archive down must not block the feed path
        logger.warning("archivio Ministero non raggiungibile: %s", exc)
        archive_links = []

    known_links = {entry.link for entry in entries}
    for link in archive_links:
        if link not in known_links:
            entries.append(rss.RssEntry(
                source_id=link.rstrip("/").rsplit("/", 1)[-1],
                title=link.rsplit("/", 1)[-1].replace("-", " ").capitalize(),
                link=link,
                feed="archivio",
            ))

    existing_ids = await list_source_ids(MINISTERO_SOURCE)
    queued_entries = await pending_entries(MINISTERO_QUEUE_ID)
    pending = [_entry_from_dict(value) for value in queued_entries]
    pending = [entry for entry in pending if entry is not None]
    ordered = _merge_entries(pending, entries)
    new_candidates = [entry for entry in ordered if entry.source_id not in existing_ids]
    new_batch = new_candidates[:MAX_NEW_PAGES_PER_RUN]
    remaining = new_candidates[MAX_NEW_PAGES_PER_RUN:]

    # Re-read a small rolling window of known items to detect corrections on
    # official pages. duplicate_detector versions changed content by hash.
    # During an initial catch-up, spend the browser budget on unseen official
    # pages first. Once the queue is empty, the next run rechecks known pages
    # for corrections and creates a version snapshot when their hash changes.
    enrichment_ids = set() if new_candidates else await list_source_ids_needing_enrichment(
        MINISTERO_SOURCE, MAX_RECHECK_PAGES_PER_RUN
    )
    rechecks = [] if new_candidates else [
        entry for entry in entries if entry.source_id in (enrichment_ids or existing_ids)
    ][:MAX_RECHECK_PAGES_PER_RUN]
    fetch_entries = _merge_entries(new_batch, rechecks)
    detail = await pages.fetch_pages([entry.link for entry in fetch_entries]) if fetch_entries else {}

    pdf_targets = [page.pdf_urls[0] for page in detail.values() if page.pdf_urls]
    pdf_files: dict[str, str] = {}
    pdf_ocr: dict[str, str] = {}
    pdf_ocr_errors: dict[str, str] = {}
    if pdf_targets:
        try:
            fetched = await pages.fetch_many(pdf_targets)
            pdf_files = {url: result["file"] for url, result in fetched.items() if result.get("file")}
            pdf_ocr = {url: str(result["ocr_text"]) for url, result in fetched.items() if result.get("ocr_text")}
            pdf_ocr_errors = {url: str(result["ocr_error"]) for url, result in fetched.items() if result.get("ocr_error")}
        except Exception as exc:
            logger.warning("download PDF fallito: %s", exc)

    inserted = updated = unchanged = failed = 0
    for entry in fetch_entries:
        try:
            page = detail.get(entry.link)
            extracted: dict[str, Any] = dict(page.fields) if page else {}
            confidence: dict[str, float] = dict(page.confidence) if page else {}
            pdf_url = page.pdf_urls[0] if page and page.pdf_urls else None
            product_image_url = None
            if pdf_url and pdf_url in pdf_files:
                product_image_url = pdf.extract_product_image_from_pdf(pdf_files[pdf_url])
                parsed = pdf.extract_from_pdf_file(pdf_files[pdf_url])
                for key, value in parsed.fields.items():
                    extracted[key] = value
                    confidence[key] = parsed.confidence[key]
                # Scanned recall forms have no PDF text layer. The browser
                # fetcher renders them at high resolution and returns OCR;
                # text-layer/form values always win over OCR values.
                if pdf_url in pdf_ocr:
                    ocr_parsed = pdf.extract_from_text(pdf_ocr[pdf_url])
                    for key, value in ocr_parsed.fields.items():
                        extracted[key] = value
                        confidence[key] = ocr_parsed.confidence[key]
                    extracted["_ocr_checked"] = "1"
                elif pdf_url in pdf_ocr_errors:
                    extracted["_ocr_checked"] = "0"
                # Origin fields are extracted independently from OCR/image
                # enrichment so existing PDFs are rechecked once after the
                # parser learns a new official label.
                extracted["_origin_checked"] = "1"
            elif not pdf_url:
                # Some older archive pages have no linked official PDF. Keep
                # the fact that the page was checked so the scheduler
                # does not retry the same un-enrichable records indefinitely.
                extracted["_document_checked"] = "no_pdf"
            published = extracted.pop("published", None)
            published = (pages.italian_date_to_iso(published) if published else None) or entry.published
            recall = normalizer.normalize(
                source=MINISTERO_SOURCE, source_id=entry.source_id, title=entry.title, source_url=entry.link,
                published=published, summary=entry.summary, extracted=extracted, confidence=confidence, pdf_url=pdf_url,
            )
            recall.image_url = product_image_url or (page.image_url if page else None)
            if recall.image_url:
                recall.content_hash = normalizer.content_hash(recall.content_hash, recall.image_url)
            recall.is_seafood = _seafood(" ".join(filter(None, [
                entry.title,
                recall.risk_description,
                extracted.get("scientific_name"),
                extracted.get("production_method"),
                extracted.get("fao_area_code"),
            ])))
            if extracted.get("lot_code"):
                recall.lots = [RecallLot(lot_code=lot_code, expiration_date=extracted.get("expiration_date"))
                               for lot_code in pdf.split_lot_codes(extracted["lot_code"])]
            outcome = await upsert_recall(recall)
            if outcome == "inserted":
                inserted += 1
                await notify_for_new_recall(recall.model_dump())
            elif outcome == "updated":
                updated += 1
            else:
                unchanged += 1
        except Exception as exc:
            failed += 1
            logger.warning("richiamo Ministero %s fallito: %s", entry.source_id, exc)

    await update_source(MINISTERO_QUEUE_ID, {
        "pending_entries": [_entry_dict(entry) for entry in remaining],
        "pending_count": len(remaining),
        "last_recheck_at": datetime.now(timezone.utc),
    })
    msg = (f"Feed ufficiali letti: {len(entries)} elementi, {inserted} nuovi, {updated} aggiornati, "
           f"{unchanged} invariati, {failed} falliti; coda residua: {len(remaining)}")
    return SyncResult(source_id="", ok=failed == 0, message=msg + ".", fetched=len(entries),
                      inserted=inserted, updated=updated, unchanged=unchanged, failed=failed)


async def sync_rasff() -> SyncResult:
    entries = await rasff_service.fetch_entries()
    inserted = updated = unchanged = failed = 0
    for entry in entries:
        try:
            recall = normalizer.normalize(
                source=RASFF_SOURCE, source_id=entry.reference, title=entry.subject, source_url=entry.url,
                published=entry.validation_date, summary=f"{entry.classification} — {entry.product_category}",
            )
            recall.severity = entry.severity  # type: ignore[assignment]
            recall.category = entry.product_category
            recall.risk_description = f"{entry.subject}. Classificazione RASFF: {entry.classification}; rischio: {entry.risk_decision or 'n.d.'}."
            recall.consumer_advice = (f"Notifica {entry.reference} inviata da {entry.notifying_country}; origine: "
                                      f"{', '.join(entry.origin_countries) or 'n.d.'}. Consulta il portale RASFF per i dettagli.")
            recall.is_seafood = _seafood(entry.subject + " " + entry.product_category)
            recall.verified = True
            outcome = await upsert_recall(recall)
            inserted += outcome == "inserted"
            updated += outcome == "updated"
            unchanged += outcome == "unchanged"
        except Exception as exc:
            failed += 1
            logger.warning("notifica RASFF %s fallita: %s", entry.reference, exc)
    return SyncResult(source_id="", ok=failed == 0, fetched=len(entries), inserted=inserted, updated=updated,
                      unchanged=unchanged, failed=failed,
                      message=f"RASFF: {len(entries)} notifiche, {inserted} nuove, {updated} aggiornate, {failed} fallite.")


def _comparable_fao(doc: dict[str, Any]) -> str:
    return json.dumps({key: value for key, value in doc.items() if key not in {"_id", "id", "updated_at", "retrieved_at"}},
                      sort_keys=True, default=str)


async def sync_fao() -> SyncResult:
    docs = await fao_service.fetch_areas()
    inserted = updated = unchanged = failed = 0
    now = datetime.now(timezone.utc)
    for incoming in docs:
        try:
            existing = await get_fao_area_record(incoming["code"])
            if existing and _comparable_fao(existing) == _comparable_fao(incoming):
                unchanged += 1
                continue
            payload = {**incoming, "updated_at": now, "retrieved_at": now}
            outcome = await upsert_area(payload)
            inserted += outcome == "inserted"
            updated += outcome == "updated"
        except Exception as exc:
            failed += 1
            logger.warning("zona FAO %s fallita: %s", incoming.get("code"), exc)
    return SyncResult(source_id="", ok=failed == 0, fetched=len(docs), inserted=inserted, updated=updated,
                      unchanged=unchanged, failed=failed,
                      message=f"FAO: {len(docs)} zone, {inserted} inserite, {updated} aggiornate, {unchanged} invariate, {failed} fallite.")


async def sync_environment(source_name: str) -> SyncResult:
    """Fetch public/official environmental data and persist a source snapshot."""
    adapter = next((item for item in ADAPTERS if item.name == source_name), None)
    if adapter is None:
        return SyncResult(source_id="", ok=False, failed=1, message=f"Adapter ambientale non trovato: {source_name}.")
    status = adapter.status()
    if not status.configured:
        return SyncResult(source_id="", ok=False, failed=1, message=f"{source_name}: {status.reason}")

    # The configured datasets currently cover the Mediterranean (FAO 37).
    # Data are stored on the major area and are inherited by its subareas at
    # read time, so one bounded request serves every FAO 37.x view.
    primary_areas = await list_fao_areas({"level": 1})
    area_codes = sorted({doc["code"] for doc in primary_areas if _is_mediterranean_code(doc.get("code", ""))}) or ["37"]
    fetched = inserted = failed = 0
    for area_code in area_codes:
        try:
            docs = await adapter.fetch(area_code)
            payload = [doc.model_dump() for doc in docs]
            unique_payload = list({str(doc["id"]): doc for doc in payload if doc.get("id")}.values())
            await replace_measurements(area_code, adapter.name, unique_payload)
            fetched += len(docs)
            inserted += len(unique_payload)
        except Exception as exc:
            failed += 1
            logger.warning("dati ambientali %s/%s falliti: %s", source_name, area_code, exc)
    ok = failed == 0
    return SyncResult(
        source_id="",
        ok=ok,
        fetched=fetched,
        inserted=inserted,
        failed=failed,
        message=(f"{source_name}: {fetched} misurazioni ricevute e salvate su Supabase; "
                 f"{failed} aree fallite.") if ok else
                (f"{source_name}: sincronizzazione parziale; {fetched} misurazioni salvate, "
                 f"{failed} aree fallite. Dati precedenti mantenuti per le aree fallite."),
    )


def _is_mediterranean_code(code: str) -> bool:
    return code == "37" or code.startswith("37.")


SYNCERS = {"rss": sync_ministero, "html": sync_ministero, "rasff": sync_rasff, "wfs": sync_fao}


async def run_source(source: dict[str, Any]) -> SyncResult:
    now = datetime.now(timezone.utc)
    update: dict[str, Any] = {"last_sync_at": now}
    source_type = source.get("source_type", "")
    syncer = SYNCERS.get(source_type)
    if source_type == "api":
        try:
            result = await sync_environment(source["name"])
            result.source_id = source["id"]
            if result.ok:
                count = await count_measurements(source["name"])
                update.update({"last_successful_sync_at": now, "last_error": None, "record_count": count})
            else:
                update["last_error"] = result.message
        except Exception as exc:  # an unavailable source must never break the app
            logger.warning("sync %s failed: %s", source["name"], exc)
            result = SyncResult(source_id=source["id"], ok=False, failed=1,
                                message=f"Fonte non raggiungibile: {str(exc)[:200]}. Dati precedenti mantenuti.")
            update["last_error"] = str(exc)[:300]
        await update_source(source["id"], update)
        return result
    if syncer is None:
        result = SyncResult(source_id=source["id"], ok=False, failed=1, message=(
            f"{source['name']}: integrazione non ancora configurata (adapter pronto, mancano credenziali/endpoint ufficiali)."))
        update["last_error"] = result.message
    else:
        try:
            result = await syncer()
            result.source_id = source["id"]
            source_name = MINISTERO_SOURCE if source["source_type"] in {"rss", "html"} else RASFF_SOURCE
            count = await count_areas() if source["source_type"] == "wfs" else await count_for_source(source_name)
            if result.ok:
                update.update({"last_successful_sync_at": now, "last_error": None, "record_count": count})
            else:
                update["last_error"] = result.message
        except Exception as exc:  # an unavailable source must never break the app
            logger.warning("sync %s failed: %s", source["name"], exc)
            result = SyncResult(source_id=source["id"], ok=False, failed=1,
                                message=f"Fonte non raggiungibile: {str(exc)[:200]}. Dati precedenti mantenuti.")
            update["last_error"] = str(exc)[:300]
    await update_source(source["id"], update)
    return result
