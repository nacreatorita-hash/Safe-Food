from services.ingestion.ministero_pdf_service import extract_from_text, split_lot_codes


def test_scanned_ministero_form_extracts_labelled_fields():
    text = """RICHIAMO
Data: |31/08/2026 Marchio del prodotto: AMARETTI GALLINA
Denominazione di vendita:]AMARETTI
Nome o ragione sociale dell'OSA
a nome del quale il prodotto è |MARCUCCI ALFIO
commercializzato:
Lotto di produzione: 20/07/2027
Marchio di identificazione dello stabilimento/del produttore: |AMARETTI GALLINA
Nome del produttore: IMARCUCCI ALFIO
Sede dello stabilimento: |VIA VALLE, 5 - 40021 BORGO TOSSIGNANO (BO)
Data di scadenza o termine minimo di conservazione: ]12 MESI
Descrizione peso/volume unità di vendita: |750 GR.
Motivo del richiamo:
ETICHETTA NON CONFORME
Avvertenze:
NON CONSUMARE IL PRODOTTO, RESTITUIRLO PRESSO IL PUNTO D'ACQUISTO
nserire immagine uno: Inserire immagine due:"""

    result = extract_from_text(text)

    assert result.fields["document_date"] == "31/08/2026"
    assert result.fields["osa"] == "MARCUCCI ALFIO"
    assert result.fields["lot_code"] == "20/07/2027"
    assert result.fields["expiration_date"] == "12 MESI"
    assert result.fields["consumer_advice"].endswith("PUNTO D'ACQUISTO")


def test_split_lot_codes_keeps_date_like_lot_intact():
    assert split_lot_codes("LOT-A, LOT-B; LOT-C") == ["LOT-A", "LOT-B", "LOT-C"]
    assert split_lot_codes("20/07/2027") == ["20/07/2027"]


def test_fish_origin_fields_are_extracted_without_guessing():
    text = """Richiamo
Nome scientifico: Thunnus albacares
Metodo di produzione: pescato
Zona FAO di cattura: 37.2.2
"""

    result = extract_from_text(text)

    assert result.fields["scientific_name"] == "Thunnus albacares"
    assert result.fields["production_method"] == "pescato"
    assert result.fields["fao_area_code"] == "37.2.2"


def test_fao_code_is_extracted_from_inline_label():
    result = extract_from_text("Origine del pescato — FAO 37.2.2")

    assert result.fields["fao_area_code"] == "37.2.2"
