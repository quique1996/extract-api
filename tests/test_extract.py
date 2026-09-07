"""Golden-schema tests for /extract and /extract/batch.

Deterministic (fake LLM), so they are fast, parallel-safe and green offline.
They assert the contract: schema completeness, types, batch size, validation,
health, and graceful error handling — exactly what an eval should guarantee.
"""
import json

from tests.conftest import EXPECTED_LEAD, golden_payload


def test_health_reports_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "llm" in body and "model" in body


def test_extract_returns_required_schema(client):
    payload = golden_payload()
    r = client.post("/extract", json={"text": LEAD_TEXT, "schema_hint": LEAD_SCHEMA})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"data", "model", "tokens_generated", "error"}
    assert body["error"] is None

    data = body["data"]
    # schema completeness
    expected_keys = set(EXPECTED_LEAD)
    assert expected_keys.issubset(set(data.keys())), f"missing keys: {expected_keys - set(data)}"
    # types
    assert data["nombre"] == "Carlos Villanueva"
    assert isinstance(data["servicios_interes"], list)
    assert data["presupuesto_min"] == 8000
    assert isinstance(data["presupuesto_min"], int)
    assert data["modelo"] == "model"  # echoed model name

    # every expected field carries a real value (not empty/None)
    for key in expected_keys:
        assert data[key] is not None, f"{key} is None"


def test_extract_preserves_json_types_through_marshalling(client):
    payload = golden_payload()
    r = client.post("/extract", json={"text": LEAD_TEXT, "schema_hint": LEAD_SCHEMA})
    # integers must survive as integers, not strings or floats
    assert r.json()["data"]["presupuesto_max"] == 12000
    assert isinstance(r.json()["data"]["presupuesto_max"], int)


def test_extract_reports_error_gracefully_on_llm_failure(client, monkeypatch):
    """When the LLM raises, /extract returns error str + empty data, still 200."""
    import main

    def boom(text):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(main, "call_llm", boom)
    r = client.post("/extract", json={"text": LEAD_TEXT, "schema_hint": LEAD_SCHEMA})
    assert r.status_code == 200
    body = r.json()
    assert body["data"] == {}
    assert body["error"] == "model unavailable"
    assert body["tokens_generated"] == 0


def test_extract_missing_schema_hint_rejected(client):
    r = client.post("/extract", json={"text": LEAD_TEXT})
    assert r.status_code == 422


def test_extract_empty_text_rejected(client):
    r = client.post("/extract", json={"text": "", "schema_hint": LEAD_SCHEMA})
    assert r.status_code == 422


def test_extract_text_over_length_rejected(client):
    r = client.post(
        "/extract",
        json={"text": "x" * 200_001, "schema_hint": LEAD_SCHEMA},
    )
    assert r.status_code == 422


def test_extract_batch_returns_one_response_per_input(client):
    texts = [LEAD_TEXT] * 5
    r = client.post(
        "/extract/batch",
        json=[{"text": t, "schema_hint": LEAD_SCHEMA} for t in texts],
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 5
    for item in data:
        assert set(item.keys()) == {"data", "model", "tokens_generated", "error"}
        for key in EXPECTED_LEAD:
            assert key in item["data"] and item["data"][key] is not None


def test_extract_batch_handles_mixed_and_empty(client):
    r = client.post(
        "/extract/batch",
        json=[{"text": LEAD_TEXT, "schema_hint": LEAD_SCHEMA}] * 3,
    )
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_extract_batch_empty_list_ok(client):
    r = client.post("/extract/batch", json=[])
    assert r.status_code == 200
    assert r.json() == []
