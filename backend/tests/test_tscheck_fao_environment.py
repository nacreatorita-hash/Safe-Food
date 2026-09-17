"""FAO zone lookup + safe empty/official environment summary behavior."""


def test_fao_area_known_code(client):
    resp = client.get("/fao/areas/37.2.2")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name_it"] == "Mar Ionio"
    assert data["parent_code"] == "37.2"


def test_fao_area_unknown_code_404(client):
    resp = client.get("/fao/areas/99.9")
    assert resp.status_code == 404, resp.text


def test_environment_summary_has_three_tabs_and_no_demo_measurements(client):
    resp = client.get("/environment/summary/37.2.2")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    for tab in ["water", "sediment", "biota"]:
        assert isinstance(data[tab], list), data
    all_measurements = data["water"] + data["sediment"] + data["biota"]
    for m in all_measurements:
        assert m["is_demo"] is False
        assert m["source"]


def test_environment_adapters_report_public_and_credentialed_sources(client):
    resp = client.get("/environment/adapters")
    assert resp.status_code == 200, resp.text
    adapters = {adapter["name"]: adapter for adapter in resp.json()}
    assert set(adapters) == {"FAO Fishery Statistics", "Copernicus Marine Service", "EMODnet Chemistry", "ISPRA / SNPA"}
    assert adapters["FAO Fishery Statistics"]["configured"] is False
    assert adapters["Copernicus Marine Service"]["configured"] is False
    assert adapters["EMODnet Chemistry"]["configured"] is True
    assert adapters["ISPRA / SNPA"]["configured"] is True
