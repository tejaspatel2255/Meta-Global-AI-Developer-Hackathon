# BenchGuard

Software-only camera copilot that compiles a written procedure, watches a webcam, and warns on **specific, evidence-backed mistakes**. Meta **SAM 3.1** localises objects; **Muse Spark 1.3** compiles the SOP and reads visual attributes; **Python** owns every verdict.

Hackathon repo: [Meta-Global-AI-Developer-Hackathon](https://github.com/tejaspatel2255/Meta-Global-AI-Developer-Hackathon). Product name: BenchGuard.

## Status

Phase 0 (scaffold + contracts). Live SAM/Spark spikes are not done until `MODEL_API_KEY` is available. Do not treat any accuracy or latency number as measured until it lives in `eval/reports/`.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cd frontend && npm install
```

Copy `.env.example` to `.env` and set `MODEL_API_KEY` (server only).

```bash
make test      # offline
make lint
make schemas
make dev       # API :8000 + UI :5173
```

Without GNU make:

```bash
python -m pytest backend/tests -q
python -m ruff check backend
python -m mypy
python -m benchguard.contracts.export_schema --out frontend/src/contracts
python scripts/dev.py
```

## Docs

Start at `AGENTS.md`, then `docs/STATUS.md`, `PRD.md`, `docs/ARCHITECTURE.md`.
