"""Liveness/readiness endpoints have bounded, explicit contracts."""

import time


def test_health_does_not_require_mongodb(client):
    response = client.get("/health")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ok"


def test_readiness_is_success_or_explicit_dependency_failure(client):
    started = time.monotonic()
    response = client.get("/ready")
    elapsed = time.monotonic() - started
    assert response.status_code in (200, 503), response.text
    assert elapsed < 5, f"readiness ha superato il timeout: {elapsed:.2f}s"
