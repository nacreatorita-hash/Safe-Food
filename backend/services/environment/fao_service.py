"""Real FAO Major Fishing Areas (CWP) from the official FAO GeoServer WFS — all levels."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

WFS_URL = (
    "https://www.fao.org/fishery/geoserver/fifao/ows?service=WFS&version=1.0.0"
    "&request=GetFeature&typeName=fifao:FAO_AREAS_ERASE_LOWRES&outputFormat=json"
)
SOURCE_URL = "https://www.fao.org/fishery/en/area/search"
SOURCE_NAME = "FAO Major Fishing Areas (CWP) — GeoServer WFS"

LEVEL_ORDER = {"MAJOR": 1, "SUBAREA": 2, "DIVISION": 3, "SUBDIVISION": 4, "SUBUNIT": 5}
LEVEL_IT = {"MAJOR": "Area principale", "SUBAREA": "Sottozona", "DIVISION": "Divisione",
            "SUBDIVISION": "Sottodivisione", "SUBUNIT": "Unità"}

# Italian names for the areas most common on Italian labels; others fall back to English.
NAMES_IT: dict[str, str] = {
    "18": "Mar Artico", "21": "Atlantico nord-occidentale", "27": "Atlantico nord-orientale",
    "31": "Atlantico centro-occidentale", "34": "Atlantico centro-orientale",
    "37": "Mediterraneo e Mar Nero", "41": "Atlantico sud-occidentale", "47": "Atlantico sud-orientale",
    "48": "Atlantico antartico", "51": "Oceano Indiano occidentale", "57": "Oceano Indiano orientale",
    "58": "Oceano Indiano antartico", "61": "Pacifico nord-occidentale", "67": "Pacifico nord-orientale",
    "71": "Pacifico centro-occidentale", "77": "Pacifico centro-orientale", "81": "Pacifico sud-occidentale",
    "87": "Pacifico sud-orientale", "88": "Pacifico antartico",
    "37.1": "Mediterraneo occidentale", "37.1.1": "Baleari", "37.1.2": "Golfo del Leone", "37.1.3": "Sardegna",
    "37.2": "Mediterraneo centrale", "37.2.1": "Mar Adriatico", "37.2.2": "Mar Ionio",
    "37.3": "Mediterraneo orientale", "37.3.1": "Mar Egeo", "37.3.2": "Levante",
    "37.4": "Mar Nero", "37.4.1": "Mar di Marmara", "37.4.2": "Mar Nero", "37.4.3": "Mar d'Azov",
    "27.1": "Mare di Barents", "27.2": "Mare di Norvegia, Spitsbergen e Isola degli Orsi", "27.3": "Skagerrak, Kattegat e Baltico",
    "27.4": "Mare del Nord", "27.5": "Islanda e Faroe", "27.6": "Rockall e ovest Scozia", "27.7": "Mare d'Irlanda, ovest Irlanda, Canale della Manica",
    "27.8": "Golfo di Biscaglia", "27.9": "Acque portoghesi", "27.10": "Azzorre", "27.12": "Nord Azzorre", "27.14": "Groenlandia orientale",
}
OCEAN_IT = {"Atlantic": "Oceano Atlantico", "Pacific": "Oceano Pacifico", "Indian": "Oceano Indiano",
            "Arctic": "Mar Glaciale Artico", "Antarctic": "Oceano Antartico", "Southern": "Oceano Antartico"}


def _parent(code: str) -> str | None:
    return code.rsplit(".", 1)[0] if "." in code else None


def decimate(geometry: dict[str, Any], max_points: int = 60, max_polys: int = 6) -> dict[str, Any]:
    """Thin rings and keep only the largest polygons for the lightweight overview layer."""
    def ring(r: list) -> list:
        if len(r) <= max_points:
            return r
        step = len(r) / max_points
        out = [r[int(i * step)] for i in range(max_points)]
        return out + [r[0]]
    if geometry["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": [ring(geometry["coordinates"][0])]}
    if geometry["type"] == "MultiPolygon":
        polys = sorted(geometry["coordinates"], key=lambda p: -len(p[0]))[:max_polys]
        return {"type": "MultiPolygon", "coordinates": [[ring(p[0])] for p in polys]}
    return geometry


def _documents_from_features(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for f in features:
        p = f["properties"]
        code = p.get("F_CODE")
        level = p.get("F_LEVEL")
        if not code or level not in LEVEL_ORDER:
            continue
        name_en = p.get("NAME_EN") or p.get("F_NAME") or code
        ocean = p.get("OCEAN") or ""
        docs.append({
            "code": code,
            "name_it": NAMES_IT.get(code, name_en),
            "name_en": name_en,
            "parent_code": _parent(code),
            "level": LEVEL_ORDER[level],
            "level_label": LEVEL_IT[level],
            "ocean": OCEAN_IT.get(ocean, ocean),
            "description": f"{LEVEL_IT[level]} FAO {code} — {name_en}. {OCEAN_IT.get(ocean, ocean)}.",
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "source_record_id": p.get("ID") or f.get("id") or code,
            "geometry": f.get("geometry"),
            "geometry_overview": decimate(f["geometry"]) if f.get("geometry") else None,
        })
    return docs


async def iter_area_batches(page_size: int = 50) -> AsyncIterator[list[dict[str, Any]]]:
    """Yield bounded WFS pages so the full FAO geometry never fills RAM."""
    page_size = max(1, min(page_size, 100))
    start_index = 0
    previous_signature: tuple[str, ...] | None = None
    async with httpx.AsyncClient(timeout=60.0) as http:
        while True:
            res = await http.get(WFS_URL, params={
                "maxFeatures": str(page_size),
                "startIndex": str(start_index),
            })
            res.raise_for_status()
            features = res.json().get("features", [])
            if not features:
                break
            signature = tuple(
                str(feature.get("id") or feature.get("properties", {}).get("ID")
                    or feature.get("properties", {}).get("F_CODE") or "")
                for feature in features
            )
            if signature and signature == previous_signature:
                # Protect the worker if a WFS implementation ignores pagination.
                break
            previous_signature = signature
            batch = _documents_from_features(features)
            if batch:
                yield batch
            if len(features) < page_size:
                break
            start_index += len(features)


async def fetch_areas() -> list[dict[str, Any]]:
    """Return all area documents while fetching the official WFS in pages."""
    docs: list[dict[str, Any]] = []
    async for batch in iter_area_batches():
        docs.extend(batch)
    return docs


def bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float] | None:
    pts = []
    def walk(c):
        if isinstance(c[0], (int, float)):
            pts.append(c)
        else:
            for x in c:
                walk(x)
    walk(geometry["coordinates"])
    if not pts:
        return None
    lons = [pt[0] for pt in pts]
    lats = [pt[1] for pt in pts]
    return min(lats), min(lons), max(lats), max(lons)


__all__ = ["fetch_areas", "iter_area_batches", "bbox", "decimate", "json"]
