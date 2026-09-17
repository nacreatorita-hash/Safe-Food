"""Source synchronisation and durable ingestion bookkeeping.

The functions are shared by the admin trigger and the single scheduler
worker. Ministero discovery is incremental: only RSS entries that are not
already in Supabase enter the detail/PDF pipeline. Existing recalls are never
re-read automatically.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from models.schemas import RecallLot, SyncResult
from repositories.fao import count_areas, count_measurements, get_area_record as get_fao_area_record
from repositories.fao import list_areas as list_fao_areas
from repositories.fao import replace_measurements, upsert_area
from repositories.recalls import count_for_source, list_recent_source_records, list_source_ids, update_by_source
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
# from the durable queue, so a larger-than-usual batch is drained progressively.
MAX_NEW_PAGES_PER_RUN = 5
MAX_PDFS_PER_RUN = MAX_NEW_PAGES_PER_RUN
# A source outage must not hold the hourly cron indefinitely. New entries that
# cannot complete the detail/PDF pipeline stay in the durable queue and are
# retried on the next cycle; completed recalls are never re-analysed.
MINISTERO_RSS_TIMEOUT_SECONDS = 90.0
MINISTERO_PAGE_TIMEOUT_SECONDS = 90.0
MINISTERO_PDF_TIMEOUT_SECONDS = 120.0
MINISTERO_RECHECK_DAYS = 30
MINISTERO_RECHECK_LIMIT = 25


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


def _official_page_fingerprint(page: pages.RecallPage) -> str:
    """Fingerprint only the cheap, labelled values exposed by the official page."""
    return normalizer.content_hash(
        page.url,
        page.fields.get("brand"),
        page.fields.get("product_name"),
        page.fields.get("risk_description"),
        page.fields.get("published"),
        page.pdf_urls[0] if page.pdf_urls else None,
    )


async def _recheck_recent_ministero() -> tuple[int, int]:
    """Check recent official pages without downloading or parsing their PDFs."""
    now = datetime.now(timezone.utc)
    records = await list_recent_source_records(
        MINISTERO_SOURCE,
        now - timedelta(days=MINISTERO_RECHECK_DAYS),
        MINISTERO_RECHECK_LIMIT,
    )
    urls = [str(record["source_url"]) for record in records if record.get("source_url")]
    if not urls:
        return 0, 0

    try:
        checked_pages = await pages.fetch_pages(urls, timeout=MINISTERO_PAGE_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning("ricontrollo pagine Ministero fallito: %s", exc)
        return 0, 0

    changed = unchanged = 0
    for existing in records:
        source_url = str(existing.get("source_url") or "")
        page = checked_pages.get(source_url)
        # A challenge/partial response must never erase values already stored.
        if page is None or (not page.fields and not page.pdf_urls):
            continue

        fingerprint = _official_page_fingerprint(page)
        official_fields = dict(existing.get("official_fields") or {})
        if official_fields.get("_page_fingerprint") == fingerprint:
            unchanged += 1
            continue

        values: dict[str, Any] = {
            "official_fields": {
                **official_fields,
                "_page_fingerprint": fingerprint,
                "_page_checked_at": now.isoformat(),
                "_page_pdf_url": page.pdf_urls[0] if page.pdf_urls else "",
            },
            "retrieved_at": now,
        }
        canonical_changed = False
        for field_name in ("brand", "product_name", "risk_description"):
            page_value = page.fields.get(field_name)
            if page_value and page_value.strip() != str(existing.get(field_name) or "").strip():
                values[field_name] = page_value.strip()
                canonical_changed = True

        published = pages.italian_date_to_iso(page.fields.get("published", ""))
        if published and published != str(existing.get("published_at") or "")[:10]:
            values["published_at"] = normalizer.parse_date(published)
            canonical_changed = True

        official_pdf = page.pdf_urls[0] if page.pdf_urls else None
        if official_pdf and official_pdf != existing.get("pdf_url"):
            # Record the new official document URL; old PDFs are intentionally
            # not re-downloaded during this lightweight historical check.
            values["pdf_url"] = official_pdf
            canonical_changed = True
        if page.image_url and not existing.get("image_url"):
            values["image_url"] = page.image_url
            canonical_changed = True

        reason = page.fields.get("risk_description")
        if reason and reason.strip() != str(existing.get("risk_description") or "").strip():
            reason_low = reason.lower()
            if "revoca" in reason_low or "revocato" in reason_low or "revocata" in reason_low:
                values["risk_type"] = "altro"
                values["severity"] = "informativo"
            else:
                risk, severity = normalizer.classify_risk(
                    " ".join(filter(None, [reason, page.fields.get("product_name"), page.fields.get("brand")]))
                )
                values["risk_type"] = risk
                values["severity"] = severity
            canonical_changed = True

        if canonical_changed:
            hash_fields = {key: value for key, value in values["official_fields"].items() if key != "_page_checked_at"}
            values["content_hash"] = normalizer.content_hash(
                existing.get("source"),
                existing.get("source_id"),
                values.get("product_name", existing.get("product_name")),
                values.get("risk_description", existing.get("risk_description")),
                json.dumps(hash_fields, sort_keys=True, default=str),
            )

        if await update_by_source(MINISTERO_SOURCE, str(existing["source_id"]), values):
            changed += 1

    return changed, unchanged


async def sync_ministero() -> SyncResult:
    entries = await rss.fetch_entries(timeout=MINISTERO_RSS_TIMEOUT_SECONDS)

    existing_ids = await list_source_ids(MINISTERO_SOURCE)
    queued_entries = await pending_entries(MINISTERO_QUEUE_ID)
    pending = [_entry_from_dict(value) for value in queued_entries]
    pending = [entry for entry in pending if entry is not None]
    ordered = _merge_entries(pending, entries)
    new_candidates = [entry for entry in ordered if entry.source_id not in existing_ids]
    new_batch = new_candidates[:MAX_NEW_PAGES_PER_RUN]
    remaining = new_candidates[MAX_NEW_PAGES_PER_RUN:]

    # The RSS feed is only a discovery/index source. Detail pages and PDFs are
    # fetched for unseen entries only; historical recalls stay untouched.
    fetch_entries = new_batch
    detail = (await pages.fetch_pages(
        [entry.link for entry in fetch_entries], timeout=MINISTERO_PAGE_TIMEOUT_SECONDS
    )) if fetch_entries else {}

    # PDF rendering/OCR is the expensive part. Five is enough for the normal
    # Ministero daily volume and keeps the whole new-recall batch together.
    pdf_targets = [page.pdf_urls[0] for page in detail.values() if page.pdf_urls][:MAX_PDFS_PER_RUN]
    pdf_files: dict[str, str] = {}
    pdf_ocr: dict[str, str] = {}
    pdf_ocr_errors: dict[str, str] = {}
    if pdf_targets:
        try:
            fetched = await pages.fetch_many(pdf_targets, timeout=MINISTERO_PDF_TIMEOUT_SECONDS)
            pdf_files = {url: result["file"] for url, result in fetched.items() if result.get("file")}
            pdf_ocr = {url: str(result["ocr_text"]) for url, result in fetched.items() if result.get("ocr_text")}
            pdf_ocr_errors = {url: str(result["ocr_error"]) for url, result in fetched.items() if result.get("ocr_error")}
        except Exception as exc:
            logger.warning("download PDF fallito: %s", exc)

    inserted = updated = unchanged = failed = 0
    completed_ids: set[str] = set()
    for entry in fetch_entries:
        try:
            page = detail.get(entry.link)
            if page is None:
                failed += 1
                logger.warning("richiamo Ministero %s: pagina di dettaglio non disponibile; resta in coda", entry.source_id)
                continue
            extracted: dict[str, Any] = dict(page.fields)
            confidence: dict[str, float] = dict(page.confidence)
            pdf_url = page.pdf_urls[0] if page.pdf_urls else None
            if pdf_url and pdf_url not in pdf_files:
                failed += 1
                logger.warning("richiamo Ministero %s: PDF non disponibile; resta in coda", entry.source_id)
                continue
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
                # Some official pages have no linked PDF. The page itself is
                # still a complete source record, so do not retry it forever.
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
            completed_ids.add(entry.source_id)
        except Exception as exc:
            failed += 1
            logger.warning("richiamo Ministero %s fallito: %s", entry.source_id, exc)

    # A transient page/PDF failure must not lose a new recall. Keep failed new
    # entries before the not-yet-started part of the queue. Entries that were
    # successfully stored are filtered out on the next run by existing_ids.
    retry_batch = [entry for entry in new_batch if entry.source_id not in completed_ids]
    remaining = _merge_entries(retry_batch, remaining)
    await update_source(MINISTERO_QUEUE_ID, {
        "pending_entries": [_entry_dict(entry) for entry in remaining],
        "pending_count": len(remaining),
    })
    rechecked, recheck_unchanged = await _recheck_recent_ministero()
    await update_source(MINISTERO_QUEUE_ID, {"last_recheck_at": datetime.now(timezone.utc)})
    msg = (f"Feed ufficiali letti: {len(entries)} elementi, {len(new_candidates)} nuovi individuati, "
           f"{inserted} inseriti, {updated} aggiornati, {unchanged} invariati, {failed} falliti; "
           f"pagine recenti ricontrollate: {rechecked} aggiornate, {recheck_unchanged} invariate; "
           f"richiami storici non rianalizzati; coda residua: {len(remaining)}")
    return SyncResult(source_id="", ok=failed == 0, message=msg + ".", fetched=len(entries),
                      inserted=inserted, updated=updated, unchanged=unchanged, failed=failed)


async def sync_rasff() -> SyncResult:
    entries = await rasff_service.fetch_entries()
    existing_ids = await list_source_ids(RASFF_SOURCE)
    new_entries = [entry for entry in entries if entry.reference not in existing_ids]
    inserted = updated = unchanged = failed = 0
    for entry in new_entries:
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
                      message=f"RASFF: {len(entries)} notifiche lette, {len(new_entries)} nuove individuate, "
                              f"{inserted} inserite, {failed} fallite; notifiche storiche non rianalizzate.")


def _comparable_fao(doc: dict[str, Any]) -> str:
    return json.dumps({key: value for key, value in doc.items() if key not in {"_id", "id", "updated_at", "retrieved_at"}},
                      sort_keys=True, default=str)


async def sync_fao() -> SyncResult:
    inserted = updated = unchanged = failed = 0
    fetched = 0
    async for docs in fao_service.iter_area_batches():
        fetched += len(docs)
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
    return SyncResult(source_id="", ok=failed == 0, fetched=fetched, inserted=inserted, updated=updated,
                      unchanged=unchanged, failed=failed,
                      message=f"FAO: {fetched} zone, {inserted} inserite, {updated} aggiornate, {unchanged} invariate, {failed} fallite.")


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
