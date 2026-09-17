"""Adapter for the official Ministero della Salute recall RSS feeds.

Two feeds exist on the portal (found on https://www.salute.gov.it/new/it/altro/rss/):
  - RSS_avvisi_sicurezza_alimentare.xml  → avvisi pubblicati dal Ministero
  - RSS_avvisi_richiami_osa.xml           → richiami pubblicati dagli operatori (OSA)
The site is behind a JavaScript challenge, so requests go through the headless fetcher.
Nothing is invented: on failure the caller keeps existing records and logs the error.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

from services.ingestion.headless_fetch import FetchError, fetch_many

FEEDS = {
    "ministero": "https://www.salute.gov.it/new/rss/RSS_avvisi_sicurezza_alimentare.xml",
    "osa": "https://www.salute.gov.it/new/rss/RSS_avvisi_richiami_osa.xml",
}
RSS_URL = FEEDS["osa"]
RSS_INDEX_URL = "https://www.salute.gov.it/new/it/altro/rss/"


@dataclass
class RssEntry:
    source_id: str
    title: str
    link: str
    published: Optional[str] = None
    summary: Optional[str] = None
    feed: str = "osa"


def parse_feed(xml_text: str, feed: str) -> list[RssEntry]:
    root = ET.fromstring(xml_text.encode("utf-8"))
    entries: list[RssEntry] = []
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        title = (item.findtext("title") or "").strip()
        if not link or not title:
            continue
        entries.append(RssEntry(
            source_id=link.rstrip("/").rsplit("/", 1)[-1] or link,
            title=title,
            link=link,
            published=(item.findtext("pubDate") or "").strip() or None,
            summary=" ".join((item.findtext("description") or "").split()) or None,
            feed=feed,
        ))
    return entries


async def fetch_entries(url: Optional[str] = None) -> list[RssEntry]:
    """Fetch and parse both feeds (or a single one). Raises on transport/parse errors."""
    targets = {k: v for k, v in FEEDS.items() if url is None or v == url} or {"custom": url or ""}
    results = await fetch_many(list(targets.values()))
    entries: list[RssEntry] = []
    errors: list[str] = []
    for feed, feed_url in targets.items():
        res = results.get(feed_url, {})
        text = res.get("text") or ""
        if res.get("status") != 200 or "<rss" not in text[:500]:
            errors.append(f"{feed}: HTTP {res.get('status')} {res.get('error') or 'risposta non RSS'}")
            continue
        entries.extend(parse_feed(text, feed))
    if not entries:
        raise FetchError("; ".join(errors) or "nessun elemento nei feed")
    return entries
