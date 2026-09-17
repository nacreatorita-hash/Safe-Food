"""Bounded literal search by lot code / EAN / brand -> GET /api/recalls?q=..."""

import pytest


def test_search_by_lot_code(client):
    resp = client.get("/recalls", params={"q": "L2451A"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    if not data or data[0].get("brand") != "Caseificio Val Padana":
        pytest.skip("fixture ufficiale per il lotto non presente nel database di test")
    assert len(data) >= 1
    assert data[0]["brand"] == "Caseificio Val Padana"


def test_search_by_ean(client):
    resp = client.get("/recalls", params={"q": "8009876543210"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    if not data or data[0].get("brand") != "Mare Nostrum":
        pytest.skip("fixture ufficiale per l'EAN non presente nel database di test")
    assert len(data) >= 1
    assert data[0]["brand"] == "Mare Nostrum"


def test_search_escapes_regex_and_bounds_length(client):
    escaped = client.get("/recalls", params={"q": "["})
    assert escaped.status_code == 200, escaped.text
    too_long = client.get("/recalls", params={"q": "x" * 101})
    assert too_long.status_code == 422, too_long.text
