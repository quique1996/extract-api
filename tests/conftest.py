"""Shared pytest fixtures and offline fakes for the Extract API.

Everything here runs fully offline: `call_llm` is monkeypatched at import time,
so the suite needs no network, no Ollama, and no API key. That is the point of
these golden tests — the API is transport-agnostic (POSTs JSON), so we verify
its contract against deterministic golden payloads, not a live model.
"""
import json

import pytest
from fastapi.testclient import TestClient

from main import call_llm

# Golden lead fixture
LEAD_TEXT = (
    "Carlos Villanueva, tel 332-385-9045, quiere página web, "
    "presupuesto 8-12k MXN, lanzar antes del 15 de octubre"
)
LEAD_SCHEMA = (
    "nombre, telefono, servicios_interes (array), presupuesto_min, "
    "presupuesto_max, fecha_limite"
)
EXPECTED_LEAD = {
    "nombre": "Carlos Villanueva",
    "telefono": "332-385-9045",
    "servicios_interes": ["Página web"],
    "presupuesto_min": 8000,
    "presupuesto_max": 12000,
    "fecha_limite": "15 de octubre",
}


def golden_payload():
    """Return an already-validated JSON payload the fake LLM should return."""
    return json.loads(json.dumps(EXPECTED_LEAD))  # deep copy


@pytest.fixture(autouse=True)
def _replace_llm(monkeypatch: pytest.MonkeyPatch):
    """Swap call_llm for a deterministic fake so the app never touches network."""

    def fake_call_llm(*args, **kwargs):
        payload, tokens = golden_payload(), 279
        return payload, tokens

    monkeypatch.setattr(call_llm, "__wrapped__", None)
    monkeypatch.setattr(call_llm, "__name__", "call_llm_fake")
    monkeypatch.setattr(main, "call_llm", fake_call_llm)


@pytest.fixture
def client():
    """A TestClient for the app under test (fake LLM active via autouse fixture)."""
    return TestClient(get_app())


def get_app():
    from fastapi import FastAPI
    from main import extract, extract_batch, health

    app = FastAPI(title="Extract API (test)", version="0.1.0-test")
    app.add_api_route(
        "/extract", extract, name="extract", response_model=None
    )
    app.add_api_route(
        "/extract/batch", extract_batch, name="extract-batch", response_model=None
    )
    app.add_api_route(
        "/health", health, name="health", response_model=None
    )
    return app
