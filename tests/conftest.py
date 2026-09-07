"""Shared pytest fixtures and offline fakes for the Extract API.

Everything here runs fully offline: `call_llm` is monkeypatched at import time,
so the suite needs no network, no Ollama, and no API key. That is the point of
these golden tests — the API is transport-agnostic (POSTs JSON), so we verify
its contract against deterministic golden payloads, not a live model.
"""
import json

import pytest
from fastapi.testclient import TestClient

import main
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

    monkeypatch.setattr(main, "call_llm", fake_call_llm)


@pytest.fixture
def client():
    """A TestClient for the real app (fake LLM active via autouse fixture)."""
    from main import app

    return TestClient(app)


def get_app():
    from main import app

    return app
