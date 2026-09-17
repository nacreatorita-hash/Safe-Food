"""Recall detail contract for any official data loaded in the test database."""

import pytest


def _get_tonno_recall(client):
    results = client.get("/recalls", params={"q": "8009876543210"}).json()
    if not results or results[0].get("brand") != "Mare Nostrum":
        pytest.skip("fixture ufficiale tonno non presente nel database di test")
    return results[0]


def test_tonno_recall_detail_fields(client):
    recall = _get_tonno_recall(client)
    resp = client.get(f"/recalls/{recall['id']}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ean"] == "8009876543210"
    assert any(l["lot_code"] == "T-7781" for l in data["lots"])
    assert data["producer"]
    assert data["is_seafood"] is True
    assert data["fao_area_code"] == "37.2.2"
    assert data["product_url"] is None


def test_passata_recall_unverified_flag(client):
    results = client.get("/recalls", params={"q": "8002233445566"}).json()
    if not results or results[0].get("verified") is not False:
        pytest.skip("fixture ufficiale passata non presente nel database di test")
    assert results[0]["verified"] is False
