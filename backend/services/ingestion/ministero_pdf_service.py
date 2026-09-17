"""Extraction of recall fields from the official Ministero "modello di richiamo" PDF.

Three cases, in order of reliability:
  1. fillable AcroForm (modulo1[...].denominazione_vendita etc.) → values read directly (0.95)
  2. text layer with "Etichetta: valore" on the same line → regex (0.6–0.9)
  3. image-only scan → OCR text supplied by the browser fetcher (0.65–0.75)
Every extracted field carries a confidence score; missing values stay None — never guessed.
"""

import re
from base64 import b64encode
from dataclasses import dataclass, field
from io import BytesIO

LOW_CONFIDENCE_THRESHOLD = 0.6

# AcroForm field name fragment → canonical field
_FORM_FIELDS: dict[str, str] = {
    "denominazione_vendita": "product_name",
    "marchio_prodotto": "brand",
    "avvertenze": "consumer_advice",
    "nome_o_ragione_sociale": "osa",
    "nome_produttore": "producer",
    "marchio_stabilimento[0]": "plant_mark",
    "marchio_stabilimento[1]": "lot_code",
    "lotto": "lot_code",
    "OSA_id": "osa",
    "data_scadenza": "expiration_date",
    "peso_volume": "package_size",
    "motivo": "risk_description",
    "sede_stabilimento": "plant",
    "data[0]": "document_date",
    "zona_fao": "fao_area_code",
    "area_fao": "fao_area_code",
    "zona_di_cattura": "fao_area_code",
    "zona_di_pesca": "fao_area_code",
    "nome_scientifico": "scientific_name",
    "denominazione_scientifica": "scientific_name",
    "metodo_di_produzione": "production_method",
    "tipo_di_produzione": "production_method",
}

_LABELS = [
    "denominazione di vendita", "marchio del prodotto", "avvertenze", "nome del produttore",
    "marchio di identificazione", "lotto di produzione", "nome o ragione sociale", "data di scadenza",
    "descrizione peso", "motivo del richiamo", "sede dello stabilimento", "inserire immagine",
    "zona fao", "area fao", "zona di cattura", "zona di pesca", "nome scientifico",
    "denominazione scientifica", "metodo di produzione", "tipo di produzione",
]

_PATTERNS: dict[str, tuple[re.Pattern[str], float]] = {
    "brand": (re.compile(r"marchio del prodotto\s*:\s*(.+)", re.I), 0.85),
    "product_name": (re.compile(r"denominazione(?:\s+di\s+vendita)?\s*:\s*(.+)", re.I), 0.9),
    "lot_code": (re.compile(r"lotto(?:\s+di\s+produzione)?\s*:\s*(.+)", re.I), 0.9),
    "ean": (re.compile(r"\b(\d{13})\b"), 0.7),
    "producer": (re.compile(r"nome del produttore\s*:\s*(.+)", re.I), 0.8),
    "plant": (re.compile(r"sede dello stabilimento\s*:\s*(.+)", re.I), 0.75),
    "expiration_date": (re.compile(r"(?:data di scadenza|TMC)[^:\n]*:\s*(.+)", re.I), 0.8),
    "package_size": (re.compile(r"(?:peso|formato)[^:\n]*:\s*(.+)", re.I), 0.7),
    "risk_description": (re.compile(r"motivo del richiamo\s*:\s*(.+)", re.I), 0.7),
    "consumer_advice": (re.compile(r"avvertenze\s*:\s*(.+)", re.I), 0.7),
    "fao_area_code": (re.compile(
        r"(?:\bFAO\s*(?:area|zona)?\s*(?:di\s*)?(?:cattura|pesca)?|"
        r"\b(?:zona|area)\s*(?:FAO\s*)?(?:di\s*)?(?:cattura|pesca)(?:\s*FAO)?)"
        r"\s*[:\-]?\s*([0-9]{2}(?:\.[0-9]+){0,3})\b", re.I), 0.85),
    "scientific_name": (re.compile(
        r"(?:nome\s+scientifico|denominazione\s+scientifica|scientific\s+name|species)\s*[:\-]\s*(.+)", re.I), 0.85),
    "production_method": (re.compile(
        r"(?:metodo\s+di\s+produzione|tipo\s+di\s+produzione|production\s+(?:method|type))\s*[:\-]\s*(.+)", re.I), 0.85),
}

# OCR commonly places the value on the following line and introduces a small
# amount of noise (|, ], or a missing accent). Parse the labelled blocks first;
# the short regexes above remain the fallback for ordinary text-layer PDFs.
_OCR_LABELS: list[tuple[str, re.Pattern[str]]] = [
    ("document_date", re.compile(r"\bData\s*:", re.I)),
    ("brand", re.compile(r"Marchio\s+de(?:l|i)\s+prodotto\s*:", re.I)),
    ("product_name", re.compile(r"Denominazione\s+(?:di\s+vendita|vendita)\s*:", re.I)),
    ("osa", re.compile(r"Nome\s+o\s+ragione\s+sociale\s+dell['’]?\s*OSA", re.I)),
    ("lot_code", re.compile(r"Lotto\s+di\s+produzione\s*:", re.I)),
    ("plant_mark", re.compile(r"Marchio\s+di\s+identificazione\s+dello\s+stabilimento\s*/\s*del\s+produttore\s*:", re.I)),
    ("producer", re.compile(r"Nome\s+del\s+produttore\s*:", re.I)),
    ("plant", re.compile(r"Sede\s+dello\s+stabilimento\s*:", re.I)),
    ("expiration_date", re.compile(r"Data\s+di\s+scadenza\s+o\s+termine\s+minimo\s+di\s+conservazione\s*:", re.I)),
    ("package_size", re.compile(r"Descrizione\s+peso\s*/\s*volume\s+unità\s+di\s+vendita\s*:", re.I)),
    ("risk_description", re.compile(r"Motivo\s+del\s+richiamo\s*:", re.I)),
    ("consumer_advice", re.compile(r"Avvertenze\s*:", re.I)),
    ("fao_area_code", re.compile(
        r"(?:Zona\s+FAO|Area\s+FAO|Zona\s+(?:di\s+)?(?:cattura|pesca)(?:\s+FAO)?|"
        r"Area\s+(?:di\s+)?(?:cattura|pesca)(?:\s+FAO)?|FAO\s+(?:area|catch\s+area|fishing\s+area))\s*:\s*", re.I)),
    ("scientific_name", re.compile(
        r"(?:Nome\s+scientifico|Denominazione\s+scientifica|Scientific\s+name|Species)\s*:\s*", re.I)),
    ("production_method", re.compile(
        r"(?:Metodo\s+di\s+produzione|Tipo\s+di\s+produzione|Production\s+(?:method|type))\s*:\s*", re.I)),
]


@dataclass
class PdfExtraction:
    fields: dict[str, str] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)
    raw_text: str = ""

    @property
    def needs_review(self) -> bool:
        if not self.confidence:
            return True
        return min(self.confidence.values()) < LOW_CONFIDENCE_THRESHOLD


def _clean(value: object) -> str:
    return " ".join(str(value).split()).strip()


def _looks_like_label(value: str) -> bool:
    low = value.lower().rstrip(":").strip()
    return value.endswith(":") or any(low.startswith(lbl) for lbl in _LABELS)


def extract_from_form_fields(fields: dict) -> PdfExtraction:
    out = PdfExtraction()
    for name, meta in fields.items():
        value = meta.get("/V") if isinstance(meta, dict) else None
        if value in (None, "", "Off"):
            continue
        lowered_name = name.lower()
        for fragment, canonical in _FORM_FIELDS.items():
            if fragment.lower() in lowered_name:
                text = _clean(value)
                if text and canonical not in out.fields:
                    out.fields[canonical] = text[:300]
                    out.confidence[canonical] = 0.95
                break
    return out


def _ocr_lines(value: str) -> list[str]:
    value = value.replace("|", " ").replace("¦", " ")
    value = re.sub(r"^[\s\[\]{}:;]+", "", value)
    lines = [" ".join(line.split()).strip(" |[]{}:;") for line in value.splitlines()]
    return [line for line in lines if line and not _looks_like_label(line)]


def _clean_ocr_value(value: str) -> str:
    return " ".join(_ocr_lines(value)).strip()


def _extract_from_labelled_text(text: str) -> PdfExtraction:
    out = PdfExtraction(raw_text=text)
    matches = []
    for name, pattern in _OCR_LABELS:
        matches.extend((match.start(), match.end(), name) for match in pattern.finditer(text))
    matches.sort(key=lambda item: item[0])
    for index, (start, end, name) in enumerate(matches):
        next_start = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        block = text[start:next_start]
        raw_value = text[end:next_start]
        value = _clean_ocr_value(raw_value)
        if name == "osa":
            # In the Ministero form the explanatory label can be read after
            # the value by OCR ("... OSA |MARCUCCI ... commercializzato:").
            # Prefer the text following the visual separator.
            osa_value = re.search(r"\|\s*([^|\n]+)", block)
            if not osa_value:
                osa_value = re.search(r"commercializzato\s*:\s*([^\n]+)", block, re.I)
            value = _clean_ocr_value(osa_value.group(1) if osa_value else value)
        if name == "fao_area_code":
            code = re.search(r"\b([0-9]{2}(?:\.[0-9]+){0,3})\b", value)
            value = code.group(1) if code else ""
        if not value:
            continue
        # Image captions and scan artefacts follow the final warning. The
        # first meaningful OCR line is the safest value for these fields.
        if name in {"risk_description", "consumer_advice"}:
            raw_value = re.split(r"\b(?:i?nserire\s+immagine)\b", raw_value, maxsplit=1, flags=re.I)[0]
            # These boxes normally contain one meaningful line. Limiting the
            # OCR result prevents text from the product photo being attached
            # to the consumer advice.
            value = " ".join(_ocr_lines(raw_value)[:1])
        elif name == "scientific_name" or name == "production_method":
            value = _ocr_lines(raw_value)[0] if _ocr_lines(raw_value) else value
        elif name != "osa":
            value = _ocr_lines(raw_value)[0] if _ocr_lines(raw_value) else value
        if value and name not in out.fields:
            out.fields[name] = value[:300]
            out.confidence[name] = 0.75
    return out


def extract_from_text(text: str) -> PdfExtraction:
    out = _extract_from_labelled_text(text)
    for name, (pattern, conf) in _PATTERNS.items():
        if name in out.fields:
            continue
        match = pattern.search(text)
        if not match:
            continue  # missing stays missing — never invented
        value = _clean(match.group(1) if match.groups() else match.group(0))
        if name == "fao_area_code":
            code = re.search(r"\b([0-9]{2}(?:\.[0-9]+){0,3})\b", value)
            value = code.group(1) if code else ""
        if not value or _looks_like_label(value):
            continue  # table layout: the "value" is just the next label
        out.fields[name] = value[:300]
        out.confidence[name] = conf
    out.raw_text = text
    return out


def extract_from_pdf_file(path: str) -> PdfExtraction:
    try:
        from pypdf import PdfReader

        reader = PdfReader(path)
        form = extract_from_form_fields(reader.get_fields() or {})
        if form.fields:
            return form
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:6])
        return extract_from_text(text)
    except Exception:
        return PdfExtraction()  # unreadable → "Da verificare"


def extract_product_image_from_pdf(path: str) -> str | None:
    """Extract the product photo embedded in the Ministero recall form.

    The standard form usually embeds a bright full-page scan plus a dark mask.
    The product photo is in the lower-left image box, so the scan is rotated
    into reading orientation and cropped to that box before being stored as a
    compact JPEG data URL. When a source PDF contains a standalone bright
    image instead, that image is returned without the form crop.
    """
    try:
        from PIL import ImageStat
        from pypdf import PdfReader

        candidates = []
        for page in PdfReader(path).pages[:3]:
            for embedded in page.images:
                image = embedded.image.convert("RGB")
                if image.width < 160 or image.height < 120:
                    continue
                sample = image.resize((80, 80))
                brightness = sum(ImageStat.Stat(sample).mean) / 3
                if brightness < 115:  # skip the dark mask/background XObject
                    continue
                candidates.append(image)
        if not candidates:
            return None

        image = max(candidates, key=lambda candidate: candidate.width * candidate.height)
        is_form_scan = image.width >= 900 and image.height >= 700
        if is_form_scan:
            if image.width > image.height:
                image = image.rotate(90, expand=True)
            width, height = image.size
            # Standard Ministero model: the first product image occupies the
            # lower-left box. Keep only the photo, excluding its caption.
            image = image.crop((
                int(width * 0.08), int(height * 0.68),
                int(width * 0.52), int(height * 0.87),
            ))

        image.thumbnail((1000, 1000))
        output = BytesIO()
        image.save(output, format="JPEG", quality=88, optimize=True)
        return "data:image/jpeg;base64," + b64encode(output.getvalue()).decode("ascii")
    except Exception:
        return None


def split_lot_codes(value: str | None) -> list[str]:
    """Split a possible list of official lot codes without touching dates."""
    if not value:
        return []
    parts = re.split(r"\s*(?:[,;]|\band\b)\s*", value, flags=re.I)
    return list(dict.fromkeys(part.strip() for part in parts if part.strip()))
