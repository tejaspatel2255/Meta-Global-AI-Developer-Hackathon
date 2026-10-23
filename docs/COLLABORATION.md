# COLLABORATION

Two humans: **Prit** (stream A) and **Tejas Patel** (stream B). Shared dirs need both reviews.

## 1. Git
- Conventional Commits (`AGENTS.md §5`).
- One concern per PR; ≤ ~300 lines.
- Do not push secrets, frames, or cassettes that contain keys.
- Remote: `https://github.com/tejaspatel2255/Meta-Global-AI-Developer-Hackathon.git`

## 2. Ownership
| Area | Owner |
|---|---|
| `engine/`, `geometry/`, `compiler/`, `api/`, `export/`, `runner/` | A (Prit) |
| `meta_client/`, `perception/`, `frontend/` | B (Tejas) |
| `contracts/`, `docs/`, `config/`, `Makefile` | shared |

Touching another owner's tree → PR and tag them.

## 3. Contract-first
Pydantic in `backend/benchguard/contracts/` is source of truth. Change `docs/CONTRACTS.md` in the same PR. Run `make schemas`.
