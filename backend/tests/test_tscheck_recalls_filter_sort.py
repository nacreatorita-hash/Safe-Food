"""Recalls page filter by risk_type and sort by product name."""


def test_filter_microbiologico_count(client):
    resp = client.get("/recalls", params={"risk_type": "microbiologico"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert all(recall["risk_type"] == "microbiologico" for recall in data)


def test_filter_allergeni_count(client):
    resp = client.get("/recalls", params={"risk_type": "allergeni"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert all(recall["risk_type"] == "allergeni" for recall in data)


def test_sort_by_product_name(client):
    resp = client.get("/recalls", params={"sort": "name"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    names = [r["product_name"] for r in data]
    assert names == sorted(names), f"not sorted alphabetically: {names}"
