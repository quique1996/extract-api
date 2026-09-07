# Evaluación / Feedback

## Calidad (CI)

**Suite offline (siempre activa, sin API key):** `tests/conftest.py` + `tests/test_extract.py`.
- Casos dorados con `golden_payload()` — schema completo, tipos, batch, validación, error handling.
- Determinista: el LLM está *falsy* con un fixture, así que corre verde y rápido en CI (job `unit-tests`) y local con `pytest`.

**Evals LLM (opcionales, `marker: deepeval`):** `tests/test_deepeval.py`.
- Requiere DeepEval instalado + key LLM externa. En CI solo corren si `DEEPEVAL_ENABLED=true`.
- Si DeepEval no está instalado ni se envía la key, se *saltan* (nunca inventamos keys ni llamamos a modelo pago en CI).
- Ejecutar localmente:

```bash
pip install -r requirements.txt -r extra-requirements.txt
DEEPEVAL_ENABLED=true DEEPEVAL_API_KEY=sk-... \
  LLM_BASE_URL=http://100.105.182.36:11434/v1 \
  pytest -m "deepeval or smoke"
```

## Test local — pytest (sin Docker)

```bash
pip install -r requirements.txt -r extra-requirements.txt   # o usar venv_geekom que ya los tiene
pytest -q
```

> Nota: los tests no tocan la red/LLM real, así que **no** requieren un Docker vivo ni Ollama corriendo en la mini. El Docker (`Dockerfile` / `docker-compose.yml`) existe para el despliegue, pero en la mini no hay daemon Docker corriendo.

## Docker

Build:

```bash
docker build -f Dockerfile -t extract-api:latest .
```

Stack local (con Ollama del host como backend):

```bash
docker compose -f docker-compose.local.yml up --build
```

Env de operación:

| var | Valor por defecto | Uso |
|---|---|---|
| `LLM_BASE_URL` | `<host>/v1` via compose | endpoint Ollama |
| `LLM_MODEL` | `ornith-1.5:9b` | modelo |
