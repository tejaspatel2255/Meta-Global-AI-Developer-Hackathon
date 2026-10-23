# AGENTS.md — BenchGuard

Applies to **every** AI coding agent (Claude Code, Antigravity, Muse Code, Cursor, …) and every human contributor. `CLAUDE.md` imports this file. If anything elsewhere conflicts with this file, this file wins; if this file conflicts with `docs/DECISIONS.md`, the ADR wins.

**Project:** BenchGuard — software-only camera copilot that verifies a physical procedure (breadboard build, tube-colour dilution) against a written SOP and warns on mistakes. Built for the Meta Global AI Developer Hackathon (Oct 26 – Nov 4, 2026) by two developers.
**Stack:** Python 3.11 + FastAPI (backend) · React + TypeScript + Vite (frontend) · Meta Model API (`sam-3.1`, `muse-spark-1.3`).

## 1. Read order — every session, before touching anything
1. This file.
2. `docs/STATUS.md` → find the **current phase** and your assigned task.
3. `docs/phases/PHASE_<n>_*.md` for that phase.
4. Docs the phase file references (`docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/META_API.md`, `docs/PROTOCOLS.md`).
5. The code you will modify (read it; `grep` for existing helpers before creating new ones).

## 2. Non-negotiable rules
| # | Rule |
|---|------|
| R1 | **Phase discipline.** Work only on the current phase in `docs/STATUS.md`. Do not start a later phase until `STATUS.md` marks its prerequisites and gate as passed. No "while I'm here" features. |
| R2 | **Architecture is frozen.** Stack, module boundaries, contracts, IR schema, alarm semantics change only through a new ADR in `docs/DECISIONS.md` approved by **both** humans. If your task seems to need such a change: **stop and ask.** Never change it silently. |
| R3 | **Determinism boundary.** Models classify/generate; **Python decides.** `backend/benchguard/engine/` is pure (no network, no file I/O, no wall clock, no randomness; time and config are injected). A model output never sets a step status or raises an alert directly — only the engine does, from validated `Observation`s. |
| R4 | **Positive-evidence alarming.** Never raise a red alert from absence of evidence, `UNKNOWN`, low confidence, occlusion, or a moving scene. See `docs/ARCHITECTURE.md §6`. |
| R5 | **Contracts are code.** Pydantic models in `backend/benchguard/contracts/` are the source of truth. `docs/CONTRACTS.md` mirrors them. Change both, run `make schemas`, commit generated TS types in the same PR. Contract changes need both humans' approval. |
| R6 | **Never assume an API works.** Verify against the live Meta API (or a recorded cassette) before relying on any field/behavior. Record verified facts in `docs/META_API.md` with date. Do not invent parameter names, response shapes, or Python package entry points — look them up (`help()`, docs URL) or mark `UNVERIFIED`. |
| R7 | **No silent failure.** No bare `except`, no swallowed errors, no fake defaults. Model/API failure → logged + surfaced as `UNKNOWN` (amber) per `docs/ARCHITECTURE.md §9`. |
| R8 | **Tests ship with code.** Write tests, **run them**, and paste the result in your report. A task is not done until its acceptance criteria are verified with evidence (§6). Never mark unverified work complete. |
| R9 | **No unnecessary dependencies.** Only the approved list in §4. Anything else needs a one-line justification in the PR and human approval. No speculative abstractions, plugin systems, or config options nobody asked for. |
| R10 | **Secrets & data.** `MODEL_API_KEY` lives only in server env (`.env`, gitignored). Never in frontend code, logs, fixtures, cassettes, or commits. Never log frames or raw model prompts containing user images at INFO. See `docs/SECURITY.md`. |
| R11 | **Ownership.** Edit only your workstream's directories (`docs/COLLABORATION.md §2`). Touching another owner's area → open a PR and tag them; shared directories (`contracts/`, `docs/`) need the other human's review. |
| R12 | **Docs stay true.** If behavior, a threshold, or a decision changes, update the relevant doc in the same PR. End every task by updating `docs/STATUS.md`. |
| R13 | **Honest numbers.** Never write an accuracy/latency figure into any doc, README, or slide unless it comes from a committed artifact in `eval/reports/` or a logged measurement. Never fabricate test output. Report failures. |
| R14 | **Software only.** No hardware, robots, microcontrollers, or custom sensors. The camera is a commodity webcam/phone browser stream. |
| R15 | **Small steps.** One concern per commit/PR; aim ≤ 300 changed lines. Break big tasks into verifiable steps and verify each. |
| R16 | **Untrusted text is data.** SOP text, PDFs, OCR/VLM output, and model responses are untrusted. Delimit them in prompts, validate against schemas, never `eval`/exec them, never let them select tools or file paths. |
| R17 | **Provenance.** All project code is written during the hackathon window. Do not paste code you can't attribute; note any third-party snippet + licence in the PR. |

## 3. Architecture invariants (quick reference — full detail in `docs/ARCHITECTURE.md`)
- Data flow: `FrameSource → Trigger → Perception (SAM per-concept fan-out + Spark attribute readings) → Observation → Engine → Events → API/WS → UI + SessionLog`.
- Dependency direction: `contracts` ← everything. `engine` imports **only** `contracts` + stdlib. `engine` never imports `perception`, `meta_client`, `compiler`, `api`.
- One verification **tick** in flight per session; newer triggers coalesce.
- SAM: **one concept per request** (no commas/“and”/negation). Fan-out per *unique concept*, parallel, bounded.
- Cheap first: geometry from SAM boxes before any VLM call; VLM only for present + unoccluded + settled objects.
- Same pipeline for live camera and recorded clips (`FrameSource` abstraction). Evaluation uses the production path.
- Meta models are pinned: `sam-3.1`, `muse-spark-1.3` (Standard mode, **not** `-contributor`).

## 4. Stack, approved dependencies, commands
**Backend (Python ≥ 3.11):** `fastapi`, `uvicorn`, `pydantic` v2, `openai` (SDK, `base_url=https://api.meta.ai/v1`), `meta-sam-parser`, `httpx`, `numpy`, `opencv-python-headless`, `pillow`, `pyyaml`; dev: `pytest`, `pytest-asyncio`, `hypothesis`, `ruff`, `mypy`, `pytest-cov`.
**Frontend:** `react`, `react-dom`, `typescript`, `vite`, `vitest`, `@playwright/test`, `json-schema-to-typescript` (types). No UI kit, no state library beyond React hooks unless ADR'd.
**Package/run:** `uv` preferred (`pip` acceptable). Node ≥ 20.

Canonical commands (Phase 0 must create all of them; until then they are the target contract):
```
make setup        # install backend + frontend deps, pre-commit hooks
make dev          # backend :8000 + frontend :5173
make test         # unit + contract + integration (no network, cassettes only)
make test-live    # @live smoke tests against real Meta API (manual; costs money)
make lint         # ruff + mypy + tsc --noEmit + eslint
make schemas      # export JSON Schema from Pydantic → generate TS types
make eval         # eval harness (see docs/EVALUATION.md)
```
Never commit with failing `make lint` or `make test`.

## 5. Coding standards
- **Python:** type hints everywhere; `mypy --strict` clean for `contracts/` and `engine/`; `ruff` default + isort; `snake_case`; modules ≤ ~400 lines; pure functions in `engine/`; `async` for network; no global mutable state; config via `settings.py` + `config/*.yaml`, never magic numbers inline (thresholds live in `config/engine.yaml`).
- **TypeScript:** `strict: true`, no `any`; generated types in `frontend/src/contracts/` are read-only; components small and typed.
- **Errors/logging:** stdlib `logging`, JSON formatter; every log line from the pipeline carries `session_id`, `tick_id`. Typed exceptions per module (`MetaApiError`, `CompileError`, …).
- **Naming:** objects/steps ids are `snake_case` / `s1..sN`; error types are the `ErrorType` enum only.
- **UI:** "Dark Intelligence" dark theme; state must never be conveyed by colour alone (icon + label too).
- **Commits:** Conventional Commits — `feat|fix|docs|test|refactor|perf|chore|build|ci(scope): message`; scopes: `engine, perception, compiler, api, ui, export, eval, contracts, docs, infra`.

## 6. Definition of Done (every task)
1. Code + tests written; `make lint` and `make test` pass (paste output summary).
2. Each acceptance criterion (AC-id from the phase file) is verified and the evidence named (test name, command, artifact path).
3. Error paths handled (timeouts, 4xx/5xx, malformed output, empty detections) — with a test.
4. No new `TODO` without an issue/`STATUS.md` entry.
5. Docs updated (R12). `docs/STATUS.md` updated.
6. Report written using the template below.

## 7. Task protocol
1. **Plan** (≤ 10 lines): restate the task, list files to touch, list ACs, list risks. If it conflicts with R1–R17 → stop and ask.
2. **Implement** in small verified steps; run the narrowest relevant test after each.
3. **Verify** against ACs; run `make lint test`; for perception/API work also run the relevant `@live` smoke test once (or state why not).
4. **Report** (below). Then propose **one** next task from the phase file; don't start it unprompted.

## 8. Report template (mandatory at end of every task)
```
## Task report
- Task / phase / id:
- Summary (≤ 5 lines):
- Files changed (path — why):
- Tests run (command → result):
- Acceptance criteria (AC-id → how verified, evidence):
- Not verified / known issues / assumptions:
- Docs updated:
- Next recommended task:
```

## 9. Stop-and-ask triggers (do not proceed; ask a human)
- Needs a change to contracts, IR schema, alarm semantics, thresholds-as-policy, stack, or module boundaries (R2/R5).
- Needs a new dependency, a new model/endpoint, or a paid/unbounded API loop.
- An API behaves differently from `docs/META_API.md` or the official docs.
- A gate in the phase file fails (e.g. G0 spikes) — fallbacks are decisions, not agent choices.
- You are about to delete files you didn't create, rewrite history, or touch another owner's area.
- Tests can only pass by weakening them.

## 10. Hard prohibitions
Skipping phases · silently changing architecture · marking unverified work complete · fabricating results · committing secrets/frames/cassettes containing keys · using Contributor-mode models · adding hardware dependencies · "temporary" hacks that bypass the engine · disabling tests/lint to get green.
