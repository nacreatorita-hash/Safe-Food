"""RASFF Window (European Commission) — public backend used by the official web interface.

No API key required. Only notifications involving Italy (notifying or origin country) are kept.
"""

from dataclasses import dataclass
from typing import Any, Optional

import httpx

SEARCH_URL = "https://webgate.ec.europa.eu/rasff-window/backend/public/notification/search/consolidated/en/"
VIEW_URL = "https://webgate.ec.europa.eu/rasff-window/screen/search?event={ref}"
PORTAL_URL = "https://webgate.ec.europa.eu/rasff-window/screen/list"

_RISK_SEVERITY = {"serious": "grave", "potentially serious": "attenzione", "not serious": "informativo"}


@dataclass
class RasffEntry:
    notif_id: int
    reference: str
    subject: str
    validation_date: Optional[str]
    classification: str
    product_category: str
    risk_decision: str
    notifying_country: str
    origin_countries: list[str]

    @property
    def severity(self) -> str:
        return _RISK_SEVERITY.get(self.risk_decision.lower(), "attenzione")

    @property
    def url(self) -> str:
        return VIEW_URL.format(ref=self.reference)


def _entry(raw: dict[str, Any]) -> RasffEntry:
    return RasffEntry(
        notif_id=raw.get("notifId", 0),
        reference=raw.get("reference", ""),
        subject=raw.get("subject", ""),
        validation_date=raw.get("ecValidationDate"),
        classification=(raw.get("notificationClassification") or {}).get("description", ""),
        product_category=(raw.get("productCategory") or {}).get("description", ""),
        risk_decision=(raw.get("riskDecision") or {}).get("description", ""),
        notifying_country=(raw.get("notifyingCountry") or {}).get("isoCode", ""),
        origin_countries=[c.get("isoCode", "") for c in raw.get("originCountries") or []],
    )


async def fetch_entries(pages: int = 3, per_page: int = 50, country: str = "IT") -> list[RasffEntry]:
    entries: list[RasffEntry] = []
    async with httpx.AsyncClient(timeout=40.0) as http:
        for page in range(1, pages + 1):
            res = await http.post(SEARCH_URL, json={"parameters": {"pageNumber": page, "itemsPerPage": per_page}})
            res.raise_for_status()
            data = res.json()
            for raw in data.get("notifications", []):
                e = _entry(raw)
                if (raw.get("productType") or {}).get("description") not in (None, "food", "feed", "food contact material"):
                    continue
                if country in (e.notifying_country, *e.origin_countries):
                    entries.append(e)
            if page >= int(data.get("totalPages", 1)):
                break
    return entries
