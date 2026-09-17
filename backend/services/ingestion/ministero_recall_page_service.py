"""Official recall page + archive: second verification path, independent from RSS.

The page exposes labelled fields in plain text ("Marca:", "Denominazione:",
"Motivo della segnalazione:", "Data pubblicazione:") and a link to the official PDF.
"""

import html as html_lib
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from services.ingestion.headless_fetch import fetch_many

ARCHIVE_URL = "https://www.salute.gov.it/new/it/avvisi/avvisi-e-richiami-di-prodotti-alimentari/"

_PDF_RE = re.compile(r'href="([^"]+\.pdf[^"]*)"', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_FIELDS = {
    "brand": re.compile(r"Marca:\s*(.+)"),
    "product_name": re.compile(r"Denominazione:\s*(.+)"),
    "risk_description": re.compile(r"Motivo della segnalazione:\s*(.+)"),
    "published": re.compile(r"Data pubblicazione:\s*(.+)"),
}
_MONTHS = {m: i for i, m in enumerate(
    ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
     "agosto", "settembre", "ottobre", "novembre", "dicembre"], start=1)}


@dataclass
class RecallPage:
    url: str
    pdf_urls: list[str]
    fields: dict[str, str] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)
    image_url: str | None = None


def _text(html: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    body = re.sub(r"<br\s*/?>|</p>|</li>|</div>|</h\d>", "\n", body, flags=re.I)
    return html_lib.unescape(_TAG_RE.sub(" ", body))


def italian_date_to_iso(value: str) -> str | None:
    m = re.search(r"(\d{1,2})\s+([a-zà]+)\s+(\d{4})", value.lower())
    if not m or m.group(2) not in _MONTHS:
        return None
    return f"{m.group(3)}-{_MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"


def parse_page(url: str, html: str) -> RecallPage:
    text = _text(html)
    page = RecallPage(url=url, pdf_urls=[urljoin(url, m) for m in dict.fromkeys(_PDF_RE.findall(html))])
    for name, rx in _FIELDS.items():
        m = rx.search(text)
        if m:
            value = " ".join(m.group(1).split()).strip()
            if value:
                page.fields[name] = value
                page.confidence[name] = 0.95  # labelled field on the official page
    img = re.search(r'<main[^>]*>.*?<img[^>]+src="([^"]+)"', html, flags=re.S)
    if img and "static/" not in img.group(1):
        page.image_url = urljoin(url, img.group(1))
    return page


async def fetch_pages(urls: list[str]) -> dict[str, RecallPage]:
    results = await fetch_many(urls)
    pages: dict[str, RecallPage] = {}
    for url in urls:
        res = results.get(url, {})
        if res.get("status") == 200 and res.get("text"):
            pages[url] = parse_page(url, res["text"])
    return pages


async def list_archive_links() -> list[str]:
    """Cross-check: every recall link present on the official archive page."""
    results = await fetch_many([ARCHIVE_URL])
    html = results.get(ARCHIVE_URL, {}).get("text") or ""
    hrefs = re.findall(r'href="([^"]*(?:avviso-sicurezza-alimentare|avvisi-sicurezza-alimentare)/[^"]+)"', html)
    return sorted({urljoin(ARCHIVE_URL, h) for h in hrefs})
