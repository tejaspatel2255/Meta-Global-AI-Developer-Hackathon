# STATUS — BenchGuard

**Current phase:** 0 — Scaffold  
**Active task:** P0-1 repo scaffold, contracts, `make` targets, GitHub remote  
**Gate G0 (spikes S1–S6):** not started (needs live `MODEL_API_KEY`)

## Phase board
| Phase | Title | Status |
|---|---|---|
| 0 | Scaffold, contracts, Make, health, docs layout | **in progress** |
| 1 | Geometry + deterministic engine | blocked on G0? no — can start after P0 gate |
| 2 | Meta client + perception + cassettes | needs key for live; cassettes after S2 |
| 3 | Compiler + protocol gold IR | after contracts stable |
| 4 | Session runner + REST/WS + export | after engine + perception stubs |
| 5 | Live UI | after API events |
| 6 | Eval harness + README results | after clip path |

## P0 checklist
- [x] Docs moved under `docs/`
- [x] Pydantic contracts + tests
- [x] `compiler/lint.py` + tests
- [x] FastAPI `/health`
- [x] Frontend shell
- [x] `make setup test lint schemas`
- [ ] GitHub `origin` pushed

## Notes
- Planning docs existed at repo root; they now live in `docs/` to match `AGENTS.md`.
- Live Meta API spikes are **not** part of the first push (no key in this session).
