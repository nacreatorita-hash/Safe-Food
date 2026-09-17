"""Idempotent development seed for official source registrations.

The default command only upserts source configuration and indexes. Cleanup of
legacy demo records or source pruning is opt-in and refuses production-like
profiles and database names.
"""

import argparse
import asyncio
import os

from lib.db import ensure_indexes
from models.schemas import DataSource
from repositories.sources import prune_sources as repository_prune_sources
from repositories.sources import purge_demo as repository_purge_demo
from repositories.sources import upsert_source
from services.environment.fao_service import WFS_URL
from services.ingestion.ministero_recall_page_service import ARCHIVE_URL
from services.ingestion.ministero_rss_service import RSS_INDEX_URL
from services.ingestion.rasff_service import PORTAL_URL

SOURCES = [
    DataSource(id="src-ministero-rss", name="Ministero della Salute — feed richiami", url=RSS_INDEX_URL,
               source_type="rss", schedule="ogni ora"),
    DataSource(id="src-ministero-archivio", name="Ministero della Salute — archivio richiami", url=ARCHIVE_URL,
               source_type="html", schedule="solo manuale"),
    DataSource(id="src-rasff", name="RASFF — Commissione Europea", url=PORTAL_URL,
               source_type="rasff", schedule="ogni 6 ore"),
    DataSource(id="src-fao", name="FAO Major Fishing Areas (WFS)", url=WFS_URL,
               source_type="wfs", schedule="solo manuale"),
    # Environmental model data are outside the app's fishing-origin scope.
    # Keep the source visible for traceability, but do not schedule syncs.
    DataSource(id="src-copernicus", name="Copernicus Marine Service", url="https://marine.copernicus.eu/",
               source_type="api", schedule="non utilizzato", active=False),
    DataSource(id="src-emodnet", name="EMODnet Chemistry", url="https://emodnet.ec.europa.eu/en/chemistry",
               source_type="api", schedule="non utilizzato", active=False),
    DataSource(id="src-ispra", name="ISPRA / SNPA", url="https://www.isprambiente.gov.it/",
               source_type="api", schedule="non utilizzato", active=False),
]


def _destructive_seed_allowed() -> bool:
    profile = os.environ.get("APP_ENV", "production").strip().lower()
    explicit = os.environ.get("ALLOW_DESTRUCTIVE_SEED", "false").strip().lower() == "true"
    return profile in {"development", "test"} and explicit


async def main(*, purge_demo: bool = False, prune_sources: bool = False) -> None:
    if purge_demo or prune_sources:
        if not _destructive_seed_allowed():
            raise RuntimeError(
                "Operazione distruttiva rifiutata: richiede APP_ENV=development/test, "
                "ALLOW_DESTRUCTIVE_SEED=true e DB_NAME con suffisso _dev/_test."
            )

    await ensure_indexes()
    for source in SOURCES:
        await upsert_source(source.model_dump())

    removed_demo_recalls = removed_demo_measurements = removed_pantry = removed_sources = 0
    if purge_demo:
        removed_demo_recalls, removed_demo_measurements, removed_pantry = await repository_purge_demo()
    if prune_sources:
        removed_sources = await repository_prune_sources([source.id for source in SOURCES])

    print(
        f"seed ok: {len(SOURCES)} fonti registrate; rimossi demo={removed_demo_recalls}, "
        f"misurazioni_demo={removed_demo_measurements}, pantry={removed_pantry}, fonti={removed_sources}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Registra le fonti ufficiali senza cancellare dati per default.")
    parser.add_argument("--purge-demo", action="store_true", help="rimuove solo fixture demo note, con guardie dev/test")
    parser.add_argument("--prune-sources", action="store_true", help="rimuove fonti non presenti nell'elenco ufficiale")
    args = parser.parse_args()
    asyncio.run(main(purge_demo=args.purge_demo, prune_sources=args.prune_sources))
