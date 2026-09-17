"""Concrete adapters for the environmental data shown in the FAO area view.

EMODnet and ISPRA expose public services and therefore do not need API keys.
Copernicus Marine uses the official Toolbox and needs a Copernicus Marine
account; the dependency and credentials are checked lazily so the API can
still start when that optional integration is not installed yet.
"""

from __future__ import annotations

import asyncio
import csv
import importlib.util
import io
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

from models.schemas import EnvironmentMeasurement
from repositories.fao import get_geometry as repository_get_geometry
from services.environment import fao_service
from services.environment.base import AdapterStatus


MEDITERRANEAN_PREFIX = "37"
MEDITERRANEAN_BBOX = (30.0, -6.0, 46.5, 37.0)  # min lat, min lon, max lat, max lon
EMODNET_DEFAULT_URL = "https://erddap.emodnet-chemistry.eu/erddap"
ISPRA_DEFAULT_URL = "https://dati.isprambiente.it/sparql"
ISPRA_DATASET_URL = "https://dati.isprambiente.it/ld/ostreopsis/dataset/html"
COPERNICUS_PRODUCT_URL = "https://data.marine.copernicus.eu/product/MEDSEA_ANALYSISFORECAST_PHY_006_013/services"


def _text(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    if not result or result.lower() in {"nan", "nat", "none", "null"}:
        return None
    return result


def _float(value: Any) -> float | None:
    raw = _text(value)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _measurement_id(*parts: Any) -> str:
    identity = "|".join(_text(part) or "" for part in parts)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, identity))


def _measurement(
    *,
    area: str,
    source: str,
    source_url: str,
    parameter: str,
    label_it: str,
    sample_type: str,
    value: float | None,
    unit: str,
    measurement_date: str | None,
    latitude: float | None = None,
    longitude: float | None = None,
    depth: float | None = None,
    species: str | None = None,
    quality_flag: str,
    reference_note: str | None = None,
    identity_parts: tuple[Any, ...] = (),
) -> EnvironmentMeasurement:
    return EnvironmentMeasurement(
        id=_measurement_id(source, area, parameter, measurement_date, *identity_parts),
        fao_area_code=area,
        source=source,
        source_url=source_url,
        parameter=parameter,
        label_it=label_it,
        value=value,
        unit=unit,
        reference_note=reference_note,
        sample_type=sample_type,  # type: ignore[arg-type]
        species=species,
        depth=depth,
        latitude=latitude,
        longitude=longitude,
        measurement_date=measurement_date,
        quality_flag=quality_flag,
        is_demo=False,
        retrieved_at=datetime.now(timezone.utc),
    )


async def _area_bbox(fao_area_code: str) -> tuple[float, float, float, float]:
    """Use the official FAO polygon when available, with a safe Med fallback."""
    try:
        geometry_doc = await repository_get_geometry(fao_area_code)
        geometry = geometry_doc.get("geometry") if geometry_doc else None
        if geometry:
            area_bbox = fao_service.bbox(geometry)
            if area_bbox:
                return area_bbox
    except Exception:
        # A source sync should not fail just because an optional geometry is
        # temporarily unavailable. The source datasets are Mediterranean-wide.
        pass
    return MEDITERRANEAN_BBOX


def _is_mediterranean_area(code: str) -> bool:
    return code == MEDITERRANEAN_PREFIX or code.startswith(f"{MEDITERRANEAN_PREFIX}.")


class _UnconfiguredAdapter:
    name = ""
    docs_url = ""
    env_key = ""

    def status(self) -> AdapterStatus:
        configured = bool(os.environ.get(self.env_key))
        return AdapterStatus(
            name=self.name,
            configured=configured,
            reason="Credenziali configurate" if configured
            else f"Credenziali assenti ({self.env_key}): nessun dato reale recuperato.",
            docs_url=self.docs_url,
        )

    async def fetch(self, fao_area_code: str) -> list[EnvironmentMeasurement]:
        if not self.status().configured:
            return []
        raise NotImplementedError(f"{self.name}: adapter non disponibile")


class CopernicusService(_UnconfiguredAdapter):
    name = "Copernicus Marine Service"
    docs_url = "https://help.marine.copernicus.eu/en/articles/7949409-copernicus-marine-toolbox-introduction"
    username_key = "COPERNICUSMARINE_SERVICE_USERNAME"
    password_key = "COPERNICUSMARINE_SERVICE_PASSWORD"

    def status(self) -> AdapterStatus:
        missing = [key for key in (self.username_key, self.password_key) if not os.environ.get(key)]
        if missing:
            return AdapterStatus(
                name=self.name,
                configured=False,
                reason=f"Credenziali assenti ({', '.join(missing)}): inserire l'account Copernicus Marine.",
                docs_url=self.docs_url,
            )
        if importlib.util.find_spec("copernicusmarine") is None:
            return AdapterStatus(
                name=self.name,
                configured=False,
                reason="Dipendenza copernicusmarine non installata: installare le dipendenze backend per attivare l'adapter.",
                docs_url=self.docs_url,
            )
        return AdapterStatus(
            name=self.name,
            configured=True,
            reason="Account Copernicus Marine e Toolbox configurati.",
            docs_url=self.docs_url,
        )

    async def fetch(self, fao_area_code: str) -> list[EnvironmentMeasurement]:
        if not self.status().configured or not _is_mediterranean_area(fao_area_code):
            return []
        bounds = await _area_bbox(fao_area_code)
        return await asyncio.to_thread(self._fetch_sync, fao_area_code, bounds)

    def _fetch_sync(self, fao_area_code: str, bounds: tuple[float, float, float, float]) -> list[EnvironmentMeasurement]:
        import copernicusmarine  # type: ignore[import-not-found]

        min_lat, min_lon, max_lat, max_lon = bounds
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)
        configurations = [
            (
                "sea_temperature",
                "thetao",
                os.environ.get("COPERNICUS_TEMPERATURE_DATASET", "cmems_mod_med_phy-tem_anfc_4.2km_P1D-m"),
                "Temperatura superficiale",
                "°C",
            ),
            (
                "salinity",
                "so",
                os.environ.get("COPERNICUS_SALINITY_DATASET", "cmems_mod_med_phy-sal_anfc_4.2km_P1D-m"),
                "Salinità superficiale",
                "PSU",
            ),
        ]
        measurements: list[EnvironmentMeasurement] = []
        errors: list[str] = []
        for parameter, variable, dataset, label, unit in configurations:
            try:
                frame = copernicusmarine.read_dataframe(
                    dataset_id=dataset,
                    variables=[variable],
                    minimum_longitude=min_lon,
                    maximum_longitude=max_lon,
                    minimum_latitude=min_lat,
                    maximum_latitude=max_lat,
                    minimum_depth=0,
                    maximum_depth=1,
                    start_datetime=start.isoformat(),
                    end_datetime=now.isoformat(),
                )
                if frame is None or frame.empty:
                    continue
                for _, row in frame.head(20).iterrows():
                    value = _float(row.get(variable))
                    if value is None:
                        continue
                    measurement_date = _text(row.get("time"))
                    measurements.append(_measurement(
                        area=fao_area_code,
                        source=self.name,
                        source_url=COPERNICUS_PRODUCT_URL,
                        parameter=parameter,
                        label_it=label,
                        sample_type="water",
                        value=value,
                        unit=unit,
                        measurement_date=measurement_date,
                        latitude=_float(row.get("latitude")),
                        longitude=_float(row.get("longitude")),
                        depth=_float(row.get("depth")),
                        quality_flag="modello Copernicus Marine",
                        identity_parts=(dataset, variable, row.get("latitude"), row.get("longitude")),
                    ))
            except Exception as exc:
                errors.append(f"{parameter}: {str(exc)[:160]}")
        if errors and not measurements:
            raise RuntimeError("; ".join(errors))
        return measurements


class EmodnetService:
    name = "EMODnet Chemistry"
    docs_url = "https://emodnet.ec.europa.eu/en/emodnet-web-service-documentation"
    datasets = {
        "water": "CONTAMINANTS_MED_WATER_TIMESERIES",
        "sediment": "CONTAMINANTS_MED_SEDIMENT_TIMESERIES",
        "biota": "CONTAMINANTS_MED_BIOTA_TIMESERIES",
    }

    def status(self) -> AdapterStatus:
        endpoint = os.environ.get("EMODNET_ERDDAP_URL", EMODNET_DEFAULT_URL).strip()
        configured = endpoint.startswith(("https://", "http://"))
        return AdapterStatus(
            name=self.name,
            configured=configured,
            reason="Endpoint ERDDAP pubblico configurato; nessuna API key richiesta." if configured
            else "Endpoint EMODnet non valido: usare un URL HTTP/HTTPS.",
            docs_url=self.docs_url,
        )

    async def fetch(self, fao_area_code: str) -> list[EnvironmentMeasurement]:
        if not self.status().configured or not _is_mediterranean_area(fao_area_code):
            return []
        min_lat, min_lon, max_lat, max_lon = await _area_bbox(fao_area_code)
        start = (datetime.now(timezone.utc) - timedelta(days=365 * 7)).strftime("%Y-%m-%dT00:00:00Z")
        endpoint = os.environ.get("EMODNET_ERDDAP_URL", EMODNET_DEFAULT_URL).rstrip("/")
        measurements: list[EnvironmentMeasurement] = []
        errors: list[str] = []
        async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
            for sample_type, dataset in self.datasets.items():
                query = (
                    "time,longitude,latitude,Value,Units,P01_preflabel,CAS_no,Station_name,Water_depth"
                    f"&time>={start}&latitude>={min_lat}&latitude<={max_lat}"
                    f"&longitude>={min_lon}&longitude<={max_lon}"
                    '&S06_preflabel="Concentration"&orderByMax("time")&.limit(120)'
                )
                # Encode comparison operators and quotes; ERDDAP uses the
                # ampersands as query constraints, so those remain readable.
                url = f"{endpoint}/tabledap/{dataset}.csv?{quote(query, safe=',&=().:-')}"
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    reader = csv.DictReader(io.StringIO(response.text.lstrip("\ufeff")))
                    dataset_url = f"{endpoint}/tabledap/{dataset}.html"
                    for row in reader:
                        value = _float(row.get("Value"))
                        if value is None:
                            continue
                        parameter = _text(row.get("CAS_no")) or _text(row.get("P01_preflabel")) or "contaminant"
                        label = _text(row.get("P01_preflabel")) or "Contaminante marino"
                        label = f"Contaminante: {label[:180]}"
                        p01 = _text(row.get("P01_preflabel")) or ""
                        species_match = re.search(r"\{([^{}]+)\}", p01) if sample_type == "biota" else None
                        measurements.append(_measurement(
                            area=fao_area_code,
                            source=self.name,
                            source_url=dataset_url,
                            parameter=parameter,
                            label_it=label,
                            sample_type=sample_type,
                            value=value,
                            unit=_text(row.get("Units")) or "unità non specificata",
                            measurement_date=_text(row.get("time")),
                            latitude=_float(row.get("latitude")),
                            longitude=_float(row.get("longitude")),
                            depth=_float(row.get("Water_depth")),
                            species=species_match.group(1)[:180] if species_match else None,
                            quality_flag="dataset validato EMODnet",
                            identity_parts=(row.get("Station_name"), row.get("CAS_no"), row.get("Value")),
                        ))
                except httpx.HTTPError as exc:
                    errors.append(f"{sample_type}: {str(exc)[:160]}")
        if errors and not measurements:
            raise RuntimeError("; ".join(errors))
        return measurements


class IspraService:
    name = "ISPRA / SNPA"
    docs_url = "https://dati.isprambiente.it/ld/ostreopsis/dataset/html"
    _coordinate_re = re.compile(r"/water-sample/(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)-\(")
    query = """PREFIX top: <https://w3id.org/italia/env/onto/top/>
PREFIX imf: <https://w3id.org/italia/env/onto/inspire-mf/>
PREFIX wm: <https://w3id.org/whow/onto/water-monitoring/>
SELECT ?obs ?date ?sample ?value ?unit ?station WHERE {
  ?obs top:isPartOf <https://w3id.org/italia/env/ld/ostreopsis/dataset> ;
       wm:hasBiologicalAgent <https://w3id.org/italia/env/ld/biological-agent/110068> ;
       imf:generationTime ?time ;
       wm:hasObservationSample ?sample ;
       wm:hasResult ?result .
  ?time top:time ?date .
  ?result top:value ?value ; top:hasUnitOfMeasure ?unit .
  OPTIONAL { ?sample wm:isTakenAt ?point . ?point top:name ?station }
}
ORDER BY DESC(?date)
LIMIT 300"""

    def status(self) -> AdapterStatus:
        endpoint = os.environ.get("ISPRA_API_URL", ISPRA_DEFAULT_URL).strip()
        configured = endpoint.startswith(("https://", "http://"))
        return AdapterStatus(
            name=self.name,
            configured=configured,
            reason="Endpoint SPARQL pubblico configurato; nessuna API key richiesta." if configured
            else "Endpoint ISPRA non valido: usare un URL HTTP/HTTPS.",
            docs_url=self.docs_url,
        )

    async def fetch(self, fao_area_code: str) -> list[EnvironmentMeasurement]:
        if not self.status().configured or not _is_mediterranean_area(fao_area_code):
            return []
        endpoint = os.environ.get("ISPRA_API_URL", ISPRA_DEFAULT_URL)
        async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
            response = await client.get(endpoint, params={"query": self.query, "format": "json"})
        response.raise_for_status()
        bindings = response.json().get("results", {}).get("bindings", [])
        measurements: list[EnvironmentMeasurement] = []
        for row in bindings:
            sample_uri = row.get("sample", {}).get("value", "")
            match = self._coordinate_re.search(sample_uri)
            value_raw = row.get("value", {}).get("value")
            unit_uri = row.get("unit", {}).get("value", "")
            unit_slug = unit_uri.rstrip("/").rsplit("/", 1)[-1]
            unit = {"cell-l": "cell/L", "cell-g-fw": "cell/g peso fresco"}.get(unit_slug, unit_slug.replace("-", " "))
            measurements.append(_measurement(
                area=fao_area_code,
                source=self.name,
                source_url=ISPRA_DATASET_URL,
                parameter="ostreopsis_ovata",
                label_it="Ostreopsis ovata",
                sample_type="water",
                value=_float(value_raw),
                unit=unit or "unità non specificata",
                measurement_date=_text(row.get("date", {}).get("value")),
                latitude=_float(match.group(1)) if match else None,
                longitude=_float(match.group(2)) if match else None,
                species="Ostreopsis ovata",
                quality_flag="open data ISPRA",
                reference_note=(f"Valore ISPRA riportato come {value_raw}." if value_raw and str(value_raw).startswith("<") else None),
                identity_parts=(row.get("obs", {}).get("value"), unit_slug, value_raw),
            ))
        return measurements


class FaoService(_UnconfiguredAdapter):
    name = "FAO Fishery Statistics"
    docs_url = "https://www.fao.org/fishery/en/area/search"
    env_key = "FAO_API_KEY"


ADAPTERS = [FaoService(), CopernicusService(), EmodnetService(), IspraService()]
