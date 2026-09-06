"""
Extract API — LLM-powered structured extraction (portfolio project #3)
Arquitectura: FastAPI (Ned o cualquier nodo) -> Geekom Ollama /v1 (ornith-1.5:9b, iGPU Vulkan)
Uso: POST /extract {"text": "...", "schema_hint": "factura: emisor, receptor, total, fecha"}
"""
import json
import os
import re
import urllib.request

from fastapi import FastAPI
from pydantic import BaseModel, Field

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://100.105.182.36:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "ornith-1.5:9b")

app = FastAPI(title="Extract API", version="0.1.0")


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200_000)
    schema_hint: str = Field(..., description="Campos JSON esperados, en lenguaje natural")
    strict: bool = True


class ExtractResponse(BaseModel):
    data: dict
    model: str
    tokens_generated: int
    error: str | None = None


def call_llm(prompt: str, timeout: int = 300) -> tuple[dict, int]:
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un extractor de datos. Devuelve ÚNICAMENTE un objeto JSON válido "
                    "con los campos pedidos. Sin markdown, sin explicaciones, sin texto fuera del JSON. "
                    "Si un dato no existe en el texto, usa null."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        f"{LLM_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        res = json.load(r)
    content = res["choices"][0]["message"]["content"]
    tokens = res.get("usage", {}).get("completion_tokens", 0)
    # tolerante a fences ```json ... ``` y a razonamiento previo
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.S)
    raw = fence.group(1) if fence else content[content.find("{"): content.rfind("}") + 1]
    return json.loads(raw), tokens


@app.get("/health")
def health():
    return {"status": "ok", "llm": LLM_BASE_URL, "model": LLM_MODEL}


@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    prompt = (
        f"Extrae estos campos: {req.schema_hint}\n\n"
        f"TEXTO:\n{req.text}\n\n"
        "Responde solo el JSON."
    )
    try:
        data, tokens = call_llm(prompt)
    except Exception as e:
        return ExtractResponse(data={}, model=LLM_MODEL, tokens_generated=0, error=str(e)[:300])
    return ExtractResponse(data=data, model=LLM_MODEL, tokens_generated=tokens)


@app.post("/extract/batch", response_model=list[ExtractResponse])
async def extract_batch(reqs: list[ExtractRequest]):
    """Procesa N documentos en paralelo (Ollama encola; OLLAMA_NUM_PARALLEL=3 lo paraleliza real)."""
    import asyncio

    async def one(r: ExtractRequest) -> ExtractResponse:
        prompt = (
            f"Extrae estos campos: {r.schema_hint}\n\n"
            f"TEXTO:\n{r.text}\n\n"
            "Responde solo el JSON."
        )
        try:
            data, tokens = await asyncio.to_thread(call_llm, prompt)
            return ExtractResponse(data=data, model=LLM_MODEL, tokens_generated=tokens)
        except Exception as e:
            return ExtractResponse(data={}, model=LLM_MODEL, tokens_generated=0, error=str(e)[:300])

    return await asyncio.gather(*[one(r) for r in reqs])