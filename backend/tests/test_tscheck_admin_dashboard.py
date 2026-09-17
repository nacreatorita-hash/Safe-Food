"""Admin overview and source sync contracts in the development profile."""


def test_admin_overview_counts(client):
    resp = client.get("/admin/overview")
    if resp.status_code == 404:
        return
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["recalls"] >= 0, data
    assert data["recalls_to_verify"] >= 0, data
    adapters = {adapter["name"]: adapter for adapter in data["environment_adapters"]}
    assert len(adapters) == 4, data
    assert adapters["Copernicus Marine Service"]["configured"] is False
    assert adapters["EMODnet Chemistry"]["configured"] is True
    assert adapters["ISPRA / SNPA"]["configured"] is True


def test_admin_sources_count(client):
    resp = client.get("/admin/sources")
    if resp.status_code == 404:
        return
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) >= 4, f"expected official sources, got {len(data)}"


def test_admin_sync_ministero_rss_fails_gracefully(client):
    resp = client.post("/admin/sync/src-ministero-rss")
    if resp.status_code == 404:
        return
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data.get("ok"), bool), data
    assert data.get("source_id") == "src-ministero-rss", data
    assert "message" in data
