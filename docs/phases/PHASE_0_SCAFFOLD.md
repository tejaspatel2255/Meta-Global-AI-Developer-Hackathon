# Phase 0 — Scaffold

**Goal:** A cloneable repo where `make setup && make test && make lint` works offline, contracts are code, and `/health` runs.

## Tasks
| ID | Task | AC |
|---|---|---|
| P0-1 | Repo layout, Makefile, pyproject, frontend Vite, gitignore | AC-P0-01 |
| P0-2 | Pydantic contracts mirroring `docs/CONTRACTS.md` | AC-P0-02, AC-P0-03 |
| P0-3 | Pure `compiler/lint.py` for IR rules §2.4 | AC-P0-04 |
| P0-4 | FastAPI app: `GET /health`, `GET /models` (no live call if key missing) | AC-P0-05 |
| P0-5 | `make schemas` → JSON Schema + TS types | AC-P0-06 |
| P0-6 | Docs: STATUS, remaining design stubs, spike table unchanged | AC-P0-07 |
| P0-7 | Spikes S1–S6 | **gated** — do not fake results |

## Acceptance criteria
- **AC-P0-01** `make test` needs no network and exits 0.
- **AC-P0-02** A gold Protocol B fragment validates as `Procedure`.
- **AC-P0-03** Invalid concept / cyclic `depends_on` fail lint with typed details.
- **AC-P0-04** `engine/` imports only `contracts`, `geometry`, stdlib (enforced by a unit test on import graph).
- **AC-P0-05** `GET /health` → `{status, version}`.
- **AC-P0-06** `make schemas` writes `frontend/src/contracts/` generated types.
- **AC-P0-07** `docs/STATUS.md` names the current phase.

## Gate
Phase 0 **code gate** = AC-P0-01…07.  
Phase 0 **feasibility gate G0** = spikes S1–S4 filled in `docs/META_API.md` — separate, needs API key.

## Out of scope
Engine `step()`, SAM/Spark calls, camera UI beyond a shell, eval numbers.
