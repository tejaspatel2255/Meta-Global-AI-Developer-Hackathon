# PHASE 0 — Setup, API access, feasibility spikes (Days 1–2) · Owner: A+B · Gate **G0**

## Objectives
Working repo + CI-style checks; both devs can call `sam-3.1` and `muse-spark-1.3`; **measure** the unknowns that decide scope (latency, small-part detection, colour/orientation reading, PDF, browser capture); freeze contracts (IC-1); make go/no-go decisions (G0). **No feature code beyond scaffolding and spike scripts.**

## Prerequisites
Accepted into the hackathon (or you are not building); Official Rules read (Day 1); Meta Model API team created at dev.meta.ai/platform with both devs; kickoff has occurred (provenance — ADR-016).
Day 1 is an **evening** in IST: do T01, T02, T10 only.

## Deliverables (inputs → outputs)
Repo skeleton, `Makefile`, `.env.example`, `CODEOWNERS`, contracts v1 + generated schemas/types, `scripts/spike_*.py`, `fixtures/spike/*` (frames, raw outputs, manifests, results JSON), updated `docs/META_API.md §2/§5` (statuses → VERIFIED), filled G0 in `docs/STATUS.md`, ADR updates.

## Tasks
| ID | Owner | Task | ACs |
|---|---|---|---|
| P0-T01 | A | Scaffold: `pyproject.toml` (uv), `backend/benchguard/{contracts,geometry,engine,compiler,meta_client,perception,runner,export,api}/__init__.py`, `backend/tests/`, `frontend/` (Vite React TS), `Makefile` with **all** targets from `AGENTS.md §4` (placeholders may echo "not yet"), ruff/mypy/eslint/tsc config, `.gitignore` (`data/`, `.env`, `eval/clips/`), `.env.example`, `.github/CODEOWNERS`, LICENSE, pre-commit secret scan | AC-0.1: fresh clone → `make setup lint test` passes (empty suites OK) on **both** machines |
| P0-T02 | B | Meta API access: team, invite, keys; `scripts/list_models.py` calls `GET /v1/models`; confirm `sam-3.1` + `muse-spark-1.3` visible; minimal `@live` smoke tests (1 SAM image call, 1 Spark text+image call, 1 json_schema call) | AC-0.2: all three smoke tests pass; META_API rows 1,3,5,6,9 → VERIFIED with evidence |
| P0-T03 | A | Implement `contracts/` exactly per `docs/CONTRACTS.md`; `make schemas` (JSON Schema → TS types); example-payload round-trip tests; flattened-IR schema depth/recursion check (≤ 10, no `$ref` cycles) | AC-0.3: contract tests green; TS types compile |
| P0-T04 | B | **S1** `scripts/spike_latency.py`: 20× SAM image (1 concept, 1280×720 JPEG), 20× Spark 1-crop JSON, 20× Spark 5-crop JSON, 10× 5-concept SAM fan-out (parallel). Save p50/p95/max + failures to `fixtures/spike/latency.json` | AC-0.4: numbers recorded; **estimated tick latency** = max(SAM fan-out) + Spark 5-crop |
| P0-T05 | B | **S2** Capture ≥ 30 Protocol-A frames + ≥ 30 Protocol-B frames per `PROTOCOLS.md` shot list; run SAM for each concept; save raw outputs; **find the real Python parser entry point** (`help(meta_sam_parser)`), write `perception/sam_output.py` prototype + tests on saved outputs; compute per-concept detection rate and confidence histogram; draw boxes for eyeballing | AC-0.5: parser unit tests on real outputs; META_API rows 12,13,14,19,28 updated |
| P0-T06 | A | **S3/S4** crops from P0-T05 frames; Spark attribute reading with the production prompt (§3.2 of META_API); accuracy vs `manifest.csv` for colour (≥ 30 crops, 6 colours) and orientation (≥ 20 LED crops, both orientations; also wire-colour-on-position alternative) | AC-0.6: accuracy tables saved; META_API rows 29 updated |
| P0-T07 | A | **S5** PDF: upload SOP PDF via Files API, call Spark with `input_file`; judge extraction quality; decide in/out | AC-0.7: decision recorded (F-21 in/out); row 25 updated |
| P0-T08 | B | **S6** Browser capture: `getUserMedia` 1280×720 → JPEG q0.8 → WS binary (`CONTRACTS §6` format) → echo server saves frames; run on both dev machines; optional phone via HTTPS tunnel | AC-0.8: ≥ 60 s stable at 1 fps on both machines, frame sizes logged |
| P0-T09 | A+B | **G0 review** (below); record decisions as ADRs; update PRD NFR-01 and F-list if needed | AC-0.9: G0 row filled with both initials |
| P0-T10 | A+B | Read Official Rules + Waiver; resolve PRD §15 (track/team, models, pre-kickoff docs, deadline in IST); update ADR-012, ADR-016, STATUS | AC-0.10: answers written in `docs/DECISIONS.md` |
| P0-T11 | A | Commit `AGENTS.md`/`CLAUDE.md`/docs after kickoff; verify an agent session reads them (e.g. ask Claude Code/Antigravity/Muse Code "what is the current phase?") | AC-0.11: agent answers from STATUS.md |

## G0 — feasibility gate (both humans sign)
| Check | Pass | If fail |
|---|---|---|
| Tick latency (S1) | est. tick p95 ≤ 10 s (target 6 s) | Revise NFR-01 via ADR; "verify-at-settle" framing; reduce concepts/crops; consider Spark grounding as localiser |
| Protocol A concepts (S2) | each of `breadboard, resistor, red led, capacitor, red jumper wire, black jumper wire` detected on ≥ 80 % of relevant frames with correct count; `hand` ≥ 80 % when present | tune phrases (add attributes), closer camera/larger parts; replace part; fall back to Spark grounding for that concept |
| Protocol B tubes (S2) | `test tube` count = 5 on ≥ 90 % of frames | change tubes/rack/background; use clear vials; fixed rack markers |
| Colour (S3) | ≥ 90 % accuracy, ≥ 30 crops, 6 colours | change dyes/lighting; reduce palette; add `other` handling |
| Orientation (S4) | ≥ 80 % on ≥ 20 crops | **drop A-E4** (ADR-013), claim A-E1..E3 only |
| PDF (S5) | clean extraction on a text PDF | mark F-21 Won't |
| Capture (S6) | works on both machines | laptop webcam only; drop F-25 |
Any failure of the first four rows means **re-plan before Phase 1/2 deepen** (scope-cut ladder PRD §6.1).

## Verification
Spike outputs are artifacts (JSON/CSV/images/raw text) committed under `fixtures/spike/` (scrub: no keys; no faces). Each META_API row changed cites its file.

## Definition of Done
AC-0.1…0.11 verified · G0 signed · IC-1 tag `ic-1` pushed · `STATUS.md` updated.

## Dependencies
**Before:** none. **After:** P1 needs contracts + S5 decision; P2 needs S1–S4, S6, parser entry point; P3 needs contracts; P5 needs S4 decision (A-E4).
**Effort:** ≈ 2.5 person-days (A 1.25, B 1.25).
