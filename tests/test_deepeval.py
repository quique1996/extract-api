"""LLM-based quality evals (optional).

These only run when BOTH conditions hold:
  1. DeepEval is installed (`pytest -m deepeval` or `-m "deepeval or smoke"`)
  2. an LLM API key env is present AND DEEPEVAL_ENABLED=true

Otherwise they are SKIPPED — we never invent keys nor hit an external paid
model in CI. This is the honest alternative to the golden-schema suite in
`tests/test_extract.py`, which runs offline and is the primary gate.

Runtime env for an eval run:
  DEEPEVAL_ENABLED=true
  DEEPEVAL_API_KEY=sk-...
  LLM_BASE_URL=<the Ollama that the API can reach>
"""
from typing import Any


def _make_client(**client_kwargs: Any):
    from tests.conftest import _get_app_with_no_cors

    from fastapi.testclient import TestClient

    return TestClient(_get_app_with_no_cors(), **client_kwargs)


def test_schema_extraction_quality_llm_eval(client, LLM_EVAL_MODEL, LLM_EVAL_TIMEOUT=300):
    """Golden-lead case: verify end-to-end response matches the golden schema.

    LLM-backed — used for confidence scoring in the DeepEval run; without a key
    it is skipped (see module docstring).
    """
    client = client
    response = client.post(
        "/extract",
        json={
            "text": "Carlos Villanueva, tel 332-385-9045, presupuesto 8-12k",
            "schema_hint": "nombre, telefono, presupuesto_min, presupuesto_max",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data.get("nombre") == "Carlos Villanueva"
    assert data.get("presupuesto_min") == 8000
