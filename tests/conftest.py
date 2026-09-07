"""Shared pytest fixtures and offline fakes for Extract API.

Everything here runs fully offline: `call_llm` is monkeypatched with a
deterministic JSON factory, so no network / Ollama / API key is ever needed.
This is intentional — the API is transport-agnostic (it just POSTs JSON), so
quality is verified against golden JSON payloads, not a live model.
"""
import json
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from main import call_llm

# --------------------------------------------------------------------------- #
# Golden fixtures (single source of truth for expected extraction output)
# --------------------------------------------------------------------------- #
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


def golden_payload(text: str = LEAD_TEXT, schema: str = LEAD_SCHEMA) -> dict:
    """Return an already-validated JSON payload the fake LLM should return."""
    payload = json.loads(json.dumps(EXPECTED_LEAD))  # deep copy
    if text != LEAD_TEXT or schema != LEAD_SCHEMA:
        payload = {k: v for k, v in EXPECTED_LEAD.items()}
    # keep a couple of metadata keys the endpoint echoes through
    payload["_text_len"] = len(text)
    return payload


def make_call_llm() -> Callable[[str], tuple[dict, int]]:
    """Deterministic stand-in for call_llm: returns golden JSON + token count."""
    calls: list[str] = []

    def _fake(text: str) -> tuple[dict, int]:
        calls.append(text)
        payload = golden_payload(text)
        return payload, 279

    return _fake


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _patch_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(call_llm, "__wrapped__", None)
    monkeypatch.setattr(call_llm, "__name__", "call_llm_fake")
    monkeypatch.setattr(main, "call_llm", make_call_llm())


@pytest.fixture
def client() -> TestClient:
    return TestClient(  # type: ignore[abstract]
        _get_app_with_no_cors(),
    )


def _get_app_with_no_cors():
    """Lightweight app exposing only the endpoints under test.

    We don't import the whole module twice; TestClient runs in-process, so we
    simply import main here and return a bound client.
    """
    from fastapi import FastAPI
    from main import extract, extract_batch, health

    app = FastAPI(title="Extract API (test)", version="0.1.0-test")
    app.add_api_route("/extract", extract, methods=["POST"])
    app.add_api_route("/extract/batch", extract_batch, methods=["POST"])
    app.add_api_route("/health", health, methods=["GET"])
    return app
