"""Home page data: latest recalls list + aggregation-backed stat cards."""


def test_recalls_limit_returns_six(client):
    resp = client.get("/recalls", params={"limit": 6})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) <= 6, f"limit was not respected: got {len(data)}"


def test_recalls_stats_shape(client):
    resp = client.get("/recalls/stats")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    for key in ["total", "last_30_days", "microbiologico", "allergeni", "chimico", "fisico", "seafood"]:
        assert key in data, f"missing {key} in {data}"
    assert all(isinstance(data[key], int) and data[key] >= 0 for key in data)
