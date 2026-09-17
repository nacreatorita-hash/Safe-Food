"""Environment data adapters.

Each provider is a separate adapter behind one interface so an endpoint change never
touches the app. Where real credentials/endpoints are not configured the adapter
reports `configured = False` and returns nothing — no endpoint and no value is invented.
The seed does not create demonstration measurements; any legacy fixture must be
explicitly marked and can only be purged through the guarded dev/test command.
"""

from dataclasses import dataclass
from typing import Protocol

from models.schemas import EnvironmentMeasurement


@dataclass
class AdapterStatus:
    name: str
    configured: bool
    reason: str
    docs_url: str


class EnvironmentAdapter(Protocol):
    name: str
    docs_url: str

    def status(self) -> AdapterStatus: ...

    async def fetch(self, fao_area_code: str) -> list[EnvironmentMeasurement]: ...
