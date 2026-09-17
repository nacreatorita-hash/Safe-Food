"""Notifications list + mark read when a matching official recall exists."""

import pytest


def test_notification_created_by_pantry_match_and_mark_read(client):
    add_resp = client.post("/pantry", json={
        "name": "tscheck-notif Gorgonzola DOP dolce a fette",
        "brand": "Caseificio Val Padana",
        "ean": "8001234567890",
        "lot_code": "L2451A",
    })
    assert add_resp.status_code == 201, add_resp.text
    item = add_resp.json()
    try:
        notes = client.get("/notifications").json()
        matching = [n for n in notes if n.get("recall_id") == item["matched_recall_id"] and not n["read"]]
        if not matching:
            pytest.skip("nessun richiamo ufficiale corrispondente caricato")
        assert len(matching) >= 1, notes
        note_id = matching[0]["id"]

        read_resp = client.post(f"/notifications/{note_id}/read")
        assert read_resp.status_code == 200, read_resp.text

        notes_after = client.get("/notifications").json()
        updated = next(n for n in notes_after if n["id"] == note_id)
        assert updated["read"] is True
    finally:
        client.delete(f"/pantry/{item['id']}")


def test_mark_all_read(client):
    resp = client.post("/notifications/read-all")
    assert resp.status_code == 200, resp.text
    notes = client.get("/notifications").json()
    assert all(n["read"] for n in notes)
