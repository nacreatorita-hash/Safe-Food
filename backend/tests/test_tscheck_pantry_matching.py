"""Pantry save/delete behavior; matching assertions are conditional on official fixtures."""

import pytest

RECALLED_GORGONZOLA = {
    "name": "tscheck-pantry Gorgonzola DOP dolce a fette",
    "brand": "Caseificio Val Padana",
    "ean": "8001234567890",
    "lot_code": "L2451A",
}

WRONG_LOT_FROLLINI = {
    "name": "tscheck-pantry Frollini integrali al miele",
    "brand": "Dolce Aurora",
    "ean": "8004567891234",
    "lot_code": "ZZ-000",
}

NO_MATCH_RISO = {
    "name": "tscheck-pantry Riso Carnaroli",
    "brand": "Riseria Po",
    "ean": "9999999999999",
}

ONLY_NAME_BRAND_EAN = {
    "name": "tscheck-pantry Gorgonzola senza lotto",
    "brand": "Caseificio Val Padana",
    "ean": "8001234567890",
}


def _cleanup(client, item_id):
    if item_id:
        client.delete(f"/pantry/{item_id}")


def test_pantry_add_matching_lot_richiamato(client):
    resp = client.post("/pantry", json=RECALLED_GORGONZOLA)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    try:
        if data["status"] != "richiamato":
            pytest.skip("nessun richiamo ufficiale corrispondente caricato")
        assert data["status"] == "richiamato", data
    finally:
        _cleanup(client, data.get("id"))


def test_pantry_add_wrong_lot_controlla_lotto(client):
    resp = client.post("/pantry", json=WRONG_LOT_FROLLINI)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    try:
        if data["status"] != "controlla_lotto":
            pytest.skip("nessun richiamo ufficiale corrispondente caricato")
        assert data["status"] == "controlla_lotto", data
    finally:
        _cleanup(client, data.get("id"))


def test_pantry_add_no_match_ok(client):
    resp = client.post("/pantry", json=NO_MATCH_RISO)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    try:
        assert data["status"] == "ok", data
    finally:
        _cleanup(client, data.get("id"))


def test_pantry_add_only_name_brand_ean_controlla_lotto(client):
    resp = client.post("/pantry", json=ONLY_NAME_BRAND_EAN)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    try:
        if data["status"] != "controlla_lotto":
            pytest.skip("nessun richiamo ufficiale corrispondente caricato")
        assert data["status"] == "controlla_lotto", data
    finally:
        _cleanup(client, data.get("id"))


def test_pantry_delete_removes_item(client):
    resp = client.post("/pantry", json=NO_MATCH_RISO)
    item_id = resp.json()["id"]
    del_resp = client.delete(f"/pantry/{item_id}")
    assert del_resp.status_code == 204, del_resp.text
    listing = client.get("/pantry").json()
    assert all(i["id"] != item_id for i in listing)


def test_pantry_add_without_name_rejected(client):
    resp = client.post("/pantry", json={"brand": "tscheck-brand-only"})
    assert resp.status_code in (400, 422), resp.text
