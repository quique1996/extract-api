"""Offline golden tests for the Extract API endpoints.

Deterministic (fake LLM) and marker-tagged `smoke` so the CI `pytest -q` job
collects them while a marker-only invocation (`pytest -m deepeval`) leaves them
alone. No API key / live inference required.
"""
import pytest

from tests.conftest import EXPECTED_LEAD, LEAD_SCHEMA, LEAD_TEXT


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["model"]


def test_extract_returns_golden_schema(client):
    r = client.post(
        "/extract",
        json={"text": LEAD_TEXT, "schema_hint": LEAD_SCHEMA},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    for key in EXPECTED_LEAD:
        assert key in data
        assert data[key] is not None
    assert data["nombre"] == "Carlos Villanueva"
    assert data["telefono"] == "332-385-9045"
    assert data["presupuesto_min"] == 8000


def test_extract_int_fields_not_stringified(client):
    r = client.post(
        "/extract",
        json={"text": LEAD_TEXT, "schema_hint": LEAD_SCHEMA},
    )
    body = r.json()["data"]
    assert body["presupuesto_min"] == 8000
    assert isinstance(body["presupuesto_min"], int)
    assert isinstance(body["presupuesto_max"], int)


def test_extract_field_type_array(client):
    r = client.post(
        "/extract",
        json={"text": LEAD_TEXT, "schema_hint": LEAD_SCHEMA},
    )
    assert isinstance(r.json()["data"]["servicios_interes"], list)


def test_extract_missing_schema_hint_rejected(client):
    r = client.post("/extract", json={"text": LEAD_TEXT})
    assert r.status_code == 422


def test_extract_empty_text_rejected(client):
    r = client.post(
        "/extract", json={"text": "", "schema_hint": LEAD_SCHEMA}
    )
    assert r.status_code == 422


def test_extract_over_max_len_rejected(client):
    r = client.post(
        "/extract",
        json={"text": "x" * 200_001, "schema_hint": LEAD_SCHEMA},
    )
    assert r.status_code == 422


@pytest.mark.smoke
def test_extract_returns_json_without_error(client):
    r = client.post(
        "/extract",
        json={"text": LEAD_TEXT, "schema_hint": LEAD_SCHEMA},
    )
    assert r.status_code == 200
    assert r.json()["data"] == EXPECTED_LEAD
    assert "error" not in r.json()["data"]
