"""Normalise heterogeneous source payloads into the canonical Recall model."""

import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from models.schemas import Recall

_RISK_KEYWORDS: list[tuple[str, str, str]] = [
    ("listeria", "microbiologico", "grave"),
    ("salmonella", "microbiologico", "grave"),
    ("escherichia", "microbiologico", "grave"),
    ("botulin", "microbiologico", "grave"),
    ("norovirus", "microbiologico", "grave"),
    ("epatite", "microbiologico", "grave"),
    ("istamina", "chimico", "grave"),
    ("mercurio", "chimico", "grave"),
    ("cadmio", "chimico", "grave"),
    ("micotossin", "chimico", "grave"),
    ("aflatossin", "chimico", "grave"),
    ("ossido di etilene", "chimico", "grave"),
    ("pesticid", "chimico", "attenzione"),
    ("allergen", "allergeni", "attenzione"),
    ("arachid", "allergeni", "attenzione"),
    ("glutine", "allergeni", "attenzione"),
    ("solfiti", "allergeni", "attenzione"),
    ("corpo estraneo", "fisico", "attenzione"),
    ("corpi estranei", "fisico", "attenzione"),
    ("vetro", "fisico", "grave"),
    ("plastica", "fisico", "attenzione"),
    ("metall", "fisico", "attenzione"),
    ("rischio microbiologico", "microbiologico", "grave"),
    ("microbiologic", "microbiologico", "grave"),
    ("rischio chimico", "chimico", "grave"),
    ("chimic", "chimico", "attenzione"),
    ("rischio fisico", "fisico", "attenzione"),
    ("fisico", "fisico", "attenzione"),
    ("rischio presenza allergeni", "allergeni", "attenzione"),
    ("latte", "allergeni", "attenzione"),
    ("etichett", "etichettatura", "informativo"),
]


def classify_risk(text: str) -> tuple[str, str]:
    low = (text or "").lower()
    for keyword, risk, severity in _RISK_KEYWORDS:
        if keyword in low:
            return risk, severity
    return "altro", "attenzione"


def content_hash(*parts: Optional[str]) -> str:
    joined = "|".join((p or "").strip().lower() for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def parse_date(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def normalize(
    *,
    source: str,
    source_id: str,
    title: str,
    source_url: Optional[str],
    published: Optional[str],
    summary: Optional[str] = None,
    extracted: Optional[dict] = None,
    confidence: Optional[dict] = None,
    pdf_url: Optional[str] = None,
) -> Recall:
    extracted = extracted or {}
    confidence = confidence or {}
    haystack = " ".join(filter(None, [title, summary, extracted.get("risk_description")]))
    risk, severity = classify_risk(haystack)
    product_name = extracted.get("product_name") or re.sub(r"^richiamo\s+", "", title, flags=re.I)
    brand = extracted.get("brand")
    if not brand and summary:
        m = re.search(r"Marca:\s*(.+)", summary)
        brand = m.group(1).strip() if m else None
    return Recall(
        source=source,
        source_id=source_id,
        source_url=source_url,
        pdf_url=pdf_url,
        title=title,
        brand=brand,
        product_name=product_name.strip(),
        ean=extracted.get("ean"),
        risk_type=risk,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        risk_description=extracted.get("risk_description") or summary,
        consumer_advice=extracted.get("consumer_advice"),
        osa=extracted.get("osa"),
        producer=extracted.get("producer"),
        plant_mark=extracted.get("plant_mark"),
        plant=extracted.get("plant"),
        package_size=extracted.get("package_size"),
        expiration_date=extracted.get("expiration_date"),
        document_date=extracted.get("document_date"),
        official_fields={key: str(value) for key, value in extracted.items() if value not in (None, "")},
        published_at=parse_date(published),
        # Include every extracted field so periodic official-page rechecks can
        # version corrections to brand, risk, lot and advice, not only lot changes.
        content_hash=content_hash(source, source_id, title, summary, json.dumps(extracted, sort_keys=True, default=str)),
        verified=bool(confidence) and min(confidence.values(), default=0) >= 0.8,
        is_demo=False,
        field_confidence=confidence,
    )
