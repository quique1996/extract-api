# Extract API

LLM-powered structured extraction service. Send unstructured text (leads, invoices, emails, WhatsApp dumps) + a natural-language schema hint → get clean, typed JSON back.

**Live:** `http://100.105.182.36:8100` (Tailscale private network)
**Model:** `ornith-1.5:9b` (local, 100% on AMD Radeon 780M iGPU via Vulkan — zero API cost, zero data leaves the LAN)

## Architecture

```
Client ──POST /extract──▶ FastAPI (Geekom, :8100) ──▶ Ollama /v1 (same node, :11434)
                                                        └─ ornith-1.5:9b Q4_K_M on iGPU (Vulkan)
```

- **Inference and API co-located** on the compute node (Ryzen 9 7940HS, 16 cores) — no network hop to the LLM.
- The LLM runs **fully on the iGPU**, leaving all 16 CPU cores free for ETL/scraper jobs on the same box.
- 262K native context available for long-document extraction.
- Systemd-managed (`extract-api.service`), `Restart=on-failure`, enabled at boot.

## Measured performance (2026-09-05)

| Metric | Value |
|---|---|
| Generation | 13.0 tok/s (10.6 CPU-only → 13.0 with Vulkan + flash-attn + KV q8_0) |
| Prefill (~5k tokens) | 263 tok/s |
| Real extraction (lead → 9-field JSON, 279 tokens) | 23.5 s wall |
| Context window | 262,144 tokens (verified) |

## Usage

```bash
curl -X POST http://100.105.182.36:8100/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Carlos Villanueva, tel 332-385-9045, quiere página web, presupuesto 8-12k MXN, lanzar antes del 15 de octubre",
    "schema_hint": "nombre, telefono, servicios_interes (array), presupuesto_min, presupuesto_max, fecha_limite"
  }'
```

Response:

```json
{
  "data": {
    "nombre": "Carlos Villanueva",
    "telefono": "332-385-9045",
    "servicios_interes": ["Página web"],
    "presupuesto_min": 8000,
    "presupuesto_max": 12000,
    "fecha_limite": "15 de octubre"
  },
  "model": "ornith-1.5:9b",
  "tokens_generated": 279
}
```

## Endpoints

| Route | Method | Description |
|---|---|---|
| `/extract` | POST | Extract structured JSON from text. Body: `text`, `schema_hint`, optional `strict` |
| `/health` | GET | Service + LLM status |

## Ops (Geekom node)

```bash
sudo systemctl status extract-api
journalctl -u extract-api -f

# Ollama tuning that makes this fast (drop-in):
# /etc/systemd/system/ollama.service.d/vulkan.conf
#   OLLAMA_VULKAN=1, OLLAMA_IGPU_ENABLE=1, OLLAMA_FLASH_ATTENTION=1, OLLAMA_KV_CACHE_TYPE=q8_0
```

## Roadmap

- [ ] Batch endpoint (`/extract/batch`) — parallelize N documents across CPU cores while the iGPU streams
- [ ] Pydantic schema → prompt compiler (typed schemas instead of free-text hints)
- [ ] Webhook trigger from Telegram bot (lead capture on the go)
- [ ] RAGAS-style eval set for extraction accuracy