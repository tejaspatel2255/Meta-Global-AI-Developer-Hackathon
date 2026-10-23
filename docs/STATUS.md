# STATUS.md — Living tracker (update at the end of every task)

Agents: this is how you find the current phase and prove progress. Mark ☑ **only** with evidence named in the row. Never mark a gate passed without **both** humans' initials. Append rows; don't rewrite history.

## 1. Phase board
| Phase | File | Owner | Days | Prereqs | Gate | Status |
|---|---|---|---|---|---|---|
| P0 Setup & spikes | `phases/PHASE_0_SETUP_AND_SPIKES.md` | A+B | 1–2 | — | **G0** | ☐ not started |
| P1 Procedure compiler | `phases/PHASE_1_PROCEDURE_COMPILER.md` | A | 2–3 | P0 (S5, contracts) | — | ☐ |
| P2 Perception pipeline | `phases/PHASE_2_PERCEPTION_PIPELINE.md` | B | 2–4 | P0 (S1–S4, S6) | — | ☐ |
| P3 Step engine | `phases/PHASE_3_STEP_ENGINE.md` | A | 3–5 | contracts frozen (IC-1) | **G1** (IC-2) | ☐ |
| P4 Runner, API & live UI | `phases/PHASE_4_RUNNER_API_UI.md` | A+B | 4–6 | P2, P3 | **G2a** (IC-3) | ☐ |
| P5 Protocol hardening | `phases/PHASE_5_PROTOCOL_HARDENING.md` | A+B | 6–7 | P4 | **G2b** (IC-4, freeze) | ☐ |
| P6 Evaluation | `phases/PHASE_6_EVALUATION.md` | A+B | 5–8 | P5 freeze (test clips) | **G3** | ☐ |
| P7 Export, report & polish | `phases/PHASE_7_EXPORT_AND_POLISH.md` | A+B | 6–9 | P3/P4 | **G4** (IC-5) | ☐ |
| P8 Demo & submission | `phases/PHASE_8_DEMO_AND_SUBMISSION.md` | A+B | 9–10 | G3, G4 | submit | ☐ |
**Current phase:** P0 · **Current task:** _(set by the human at kickoff)_

## 2. Gates (both humans must initial; criteria are in the phase files)
| Gate | Question | Result | Evidence | Initials/date |
|---|---|---|---|---|
| G0 | Is the plan feasible? (latency, concept detectability, colour accuracy, orientation go/no-go, PDF go/no-go, capture works) | ☐ | `fixtures/spike/*`, `META_API.md §5` | |
| G1 | Does offline replay of dev clips produce the right alerts with 0 false red on correct clips? | ☐ | replay-E2E report | |
| G2a | Live Protocol A works end-to-end 3×correct + 1×error? | ☐ | screen recording | |
| G2b | Protocol B live + thresholds frozen + `eval-freeze-v1` tagged? | ☐ | tag, `config.sha256` | |
| G3 | Eval complete, numbers in `eval/reports/v1`, failure analysis written? | ☐ | `summary.json`, `RESULTS.md` | |
| G4 | Code freeze: fresh clone works on both machines; docs consistent? | ☐ | checklist | |

## 3. Spike board (details in `META_API.md §5`)
| S1 latency | S2 SAM parts | S3 colour | S4 orientation | S5 PDF | S6 capture | S7 SAM video (Could) |
|---|---|---|---|---|---|---|
| ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

## 4. Decisions pending (see `DECISIONS.md`)
ADR-012 track · ADR-016 pre-kickoff docs · PRD §15 open questions · **G0 outcomes:** orientation error in/out; PDF in/out; latency budget (NFR-01) confirm/revise.

## 5. Parameter log (thresholds actually in use — update when `config/*.yaml` changes)
| Param | Default | Current | Changed by/why |
|---|---|---|---|
| k_true / k_false_evidence / k_false_absence | 2 / 2 / 3 | | |
| alarm_conf_min / vlm_conf_min | 0.70 / 0.60 | | |
| settle_ms / heartbeat_ms | 700 / 6000 | | |
| occlusion_overlap | 0.25 | | |
| concept phrases (A) | breadboard, resistor, red led, capacitor, red jumper wire, black jumper wire, hand | | |
| concept phrases (B) | test tube, hand | | |

## 6. Task log (append-only; one row per completed task)
| Date | Phase/task | Who (human/agent) | PR/commit | Evidence (tests/artifacts) | Notes/known issues |
|---|---|---|---|---|---|
| 2026-10-23 | P0 Scaffold & Contracts | Dev A (Prit) | `5165b9b` | pytest 8/8 pass, health 200, mypy clean | Pushed to origin/main |
| 2026-10-23 | P1 Geometry + Engine Core | Dev A (Prit) | `feat/phase-1-geometry-engine` | 31 unit & hypothesis tests pass, 86% cov | Pure Python, 0 network, strictly deterministic |
| 2026-10-23 | P1 Procedure Compiler | Dev A (Prit) | `feat/compiler-sop-ir` | 39 unit & hypothesis tests pass | Pure SOP compiler, Gold A/B fixtures, 3-retry loop |
| 2026-10-23 | P4 Session Runner Core | Dev A (Prit) | `feat/session-runner` | 45 unit tests pass, 89% cov, mypy clean | Frame ring buffer, tick lock & coalescence, disk persistence |

## 7. Daily handoff (append; ≤ 5 lines per entry)
_blockers · what changed · next task · anything the other dev must know_
- 2026-10-23 (Prit): Implemented pure `compiler/` (prompt, schema, retry loop feeding back lint errors). Authored Gold IR and SOP text for Protocol A and verified Protocol B. 39 tests passing across compiler, engine, geometry, contracts, and health API.
- 2026-10-23 (Prit): Implemented `runner/session_runner.py` (frame ring buffer, trigger coalescence with single-tick lock, preflight checker, pub/sub event stream, and JSONL disk logging). 45 tests passing at 89% coverage.

## 8. Cut ladder status (PRD §6.1) — mark when applied
☐ C features cut · ☐ F-25/F-21/F-22 cut · ☐ F-23 cut · ☐ F-24 cut · ☐ F-20 cut · ☐ Protocol B reduced
