# PRD — BenchGuard

**Version:** 1.0 (2026-10-23) · **Owners:** Prit, Tejas Patel (@tejaspatel2255) · **Event:** Meta Global AI Developer Hackathon, Oct 26 – Nov 4, 2026 · **Track (recommended):** Indie (verify in Official Rules, Oct 26)
**Legend:** `[FACT]` verified from a cited source (see `docs/RESEARCH.md`) · `[ASSUMPTION]` unverified, must be tested · `[PROPOSAL]` our design choice. Priorities use MoSCoW: **M**ust · **S**hould · **C**ould · **W**on't.

---
## 1. One-paragraph definition
BenchGuard is a **software-only** camera copilot for hands-on work. The user pastes a written procedure; BenchGuard compiles it into machine-checkable steps, watches the workspace through a webcam/phone browser, and shows each step as green/amber/red with an evidence-backed, plain-language warning when it sees a *specific* mistake (wrong object, wrong order, wrong orientation/position/state). Meta's **SAM 3.1** locates objects, **Muse Spark 1.3** compiles the SOP and reads visual attributes on cropped regions, and **deterministic Python** owns every verdict. We validate on two protocols with a held-out, honestly reported test set.

**Tagline:** *A second pair of eyes for anyone working with their hands.*
**Honest positioning:** BenchGuard detects mistakes **as they occur or immediately after** (seconds). It does not predict mistakes in advance. A preflight check (kit present, concepts detectable) is the only "before" feature.

## 2. Problem
Physical procedures fail on small, uncaught mistakes. Chatbots can explain a protocol but cannot see whether step 4 was done correctly. Supervision doesn't scale (students, hobbyists, small shops). `[FACT]` Industrial vendors (e.g. Retrocausal, Drishti) already sell camera-based step verification for fixed assembly stations; `[FACT]` Drishti's own description mentions a training phase per deployment. `[ASSUMPTION]` the gap we target is **paste-a-procedure, zero-training setup** for non-factory settings (teaching labs, workshops, bench electronics). We make no claim about competitors' internal workflows. `[FACT]` Research on procedural mistake detection reports that end-to-end VLMs are weak at it (near-random on some benchmarks), which motivates our structure-first design (`docs/RESEARCH.md §3`).

## 3. Users & personas
| Persona | Context | Pain | What they need |
|---|---|---|---|
| **Aanya, undergrad lab student** | Teaching lab, 1 TA per 30 students | Unsupervised mistakes waste reagents/time | Step-by-step confirmation + clear "why" on errors |
| **Rohan, electronics hobbyist** | Home bench, follows written guides | Reversed parts, wrong order, no one to check | Real-time catch + explanation |
| **Meera, small-workshop lead** | 3–10 staff, manual setup procedures | Inspecting every step doesn't scale; wants a record | Verified session log she can file |
| **Judge (secondary)** | Watches 2–3 min demo + reads README | Wants novelty, technical depth, evidence it works | Live demo, numbers, honest limits |

## 4. Use cases
- **UC-1 Compile:** paste SOP → review/edit compiled steps → confirm.
- **UC-2 Preflight:** show kit to camera → BenchGuard confirms all required objects are detectable (or tells you which phrase/lighting to fix).
- **UC-3 Guided run:** work through steps; steps go green; a mistake triggers a specific warning with evidence frame.
- **UC-4 Review:** finish → verified log + report; replay where errors happened.
- **UC-5 Recorded clip:** analyse a pre-recorded clip through the same pipeline (used for evaluation and demo fallback).

## 5. Scope
### 5.1 Two protocols (hard scope — do not add a third)
Full definitions in `docs/PROTOCOLS.md`.
- **Protocol A — LED on breadboard:** place resistor, LED, battery/wires in order. Errors: wrong component (distractor), wrong order, plus **one** of {wrong orientation, wrong position} chosen by feasibility gate G0.
- **Protocol B — Colour dilution in labelled rack:** 5 tubes A–E, coloured water, 4 transfers. Errors: wrong destination tube (wrong state), wrong order, skipped step. Designed so **every error has a visible end-state signature** (colour).
`[PROPOSAL]` Claim generality only as "compiles other simple procedures" — never "works on arbitrary procedures".

### 5.2 Non-goals
Hardware of any kind · verifying pipetting **volumes**/measurements · safety-critical or biosafety certification · robots/automation control · fine-tuning/training models · multi-camera · multi-user/cloud accounts · native mobile app · public hosted live demo (API-key abuse risk).

## 6. Features (MoSCoW)
### Must (MVP)
| ID | Feature | Notes |
|---|---|---|
| F-01 | SOP text → **Procedure IR** via Muse Spark (schema-constrained) + deterministic lint | `docs/CONTRACTS.md §2` |
| F-02 | Review/edit compiled steps before start (concept phrase, enable/disable predicates, confirm) | minimal list editor |
| F-03 | Webcam capture, 1 fps JPEG to server | `getUserMedia` |
| F-04 | **Event-based ticks**: change→settle trigger, "Check now", heartbeat | server-side, OpenCV |
| F-05 | Perception: SAM per-concept fan-out + hand-occlusion gating + batched Spark attribute readings on crops | cheap-first |
| F-06 | **Deterministic step engine**: tri-state predicates, debounce, step state machine, lookahead order rules | pure Python |
| F-07 | ≥ 3 detectable error types per protocol, from `ErrorType` taxonomy | positive-evidence alarming |
| F-08 | Live UI: camera + overlay, checklist (green/amber/red + icon + text), confidence, latency badge | dark theme |
| F-09 | Alerts: written warning with reason, confidence, evidence frame ("show me why") | template-first |
| F-10 | Session log (JSONL + frames) + JSON & Markdown report | |
| F-11 | **Preflight**: kit/concept calibration + image quality check (blur/brightness) | |
| F-12 | Evaluation harness, held-out test set, README results table with CIs | `docs/EVALUATION.md` |
| F-13 | Recorded-clip path through the same pipeline (`FrameSource`) | eval + demo fallback |
| F-14 | Protocol A & B fixtures: SOP text + gold IR | |
| F-15 | Cassette record/replay for all Meta API calls | deterministic tests |
### Should
| ID | Feature |
|---|---|
| F-20 | Spoken warnings (browser TTS) |
| F-21 | PDF SOP upload via Muse Spark PDF input (gated by spike S5) |
| F-22 | LLM-polished warning text (verdict-neutral; template fallback ≤ 1.5 s) |
| F-23 | Self-contained HTML replay report (timeline + evidence frames; hostable on GitHub Pages) |
| F-24 | Regression detection (a verified step later becomes confidently false) |
| F-25 | Phone-as-camera over HTTPS tunnel |
### Could
| ID | Feature |
|---|---|
| F-30 | Voice commands ("check", "next") via Muse Voice Transcribe |
| F-31 | Hash-chained tamper-evident log |
| F-32 | "Procedure-as-code" export (Muse Spark, `ast.parse`-validated) |
| F-33 | SAM **video** tracking review mode for recorded clips (consistent object IDs) |
| F-34 | Multi-language warnings |
### Won't
Hardware · robot/pipetting-script claims · volume verification · Muse Image step cards · Muse Wonder · self-hosted Muse Spark Open/Glimmer · accounts/cloud persistence · public live demo · third protocol.

### 6.1 Scope-cut ladder (apply top-down when behind schedule; decide at integration checkpoints)
1. All **C** features. 2. F-25, F-21, F-22. 3. F-23 (keep JSON/MD report). 4. F-24. 5. F-20. 6. Protocol B reduced to 3 steps/2 error types (still must meet "≥3 types across product"). Never cut: F-06, F-07, F-11, F-12, F-13, F-15.

## 7. Innovation differentiators (each must be demonstrable)
| ID | Differentiator | How we prove it |
|---|---|---|
| D1 | **Paste-a-procedure → verifier**: SOP compiled into a closed vocabulary of checkable predicates | Demo: new SOP text → steps → preflight in < 1 min |
| D2 | **Positive-evidence alarming** + tri-state (TRUE/FALSE/UNKNOWN) with visible confidence | False-alarm rate in results table |
| D3 | **SAM→crop→Spark** pipeline: segmentation localises, VLM answers one narrow question per crop (colour, orientation) | Architecture slide; ablation if time (geometry-only vs +VLM) |
| D4 | **Evidence for every alert** (frame + overlay + reasoning) and replayable timeline | Demo + HTML report |
| D5 | **Reproducible honest evaluation**: held-out clips, Wilson CIs, frozen thresholds, one failure case shown | README table, `eval/reports/` |
| D6 | Preflight/concept calibration (kit check) | Demo |

## 8. Functional requirements
| ID | Requirement | Pri |
|---|---|---|
| FR-01 | Accept SOP as text ≤ 20 000 chars; reject larger with clear error | M |
| FR-02 | Compiler returns schema-valid IR or a typed error; lint rejects IRs violating `docs/CONTRACTS.md §2.4` | M |
| FR-03 | User can edit/disable any predicate and any object `concept` before Start | M |
| FR-04 | Preflight reports per object: found/expected/ok + image quality; blocks Start only on user's choice | M |
| FR-05 | Every tick emits an `Observation` and (if state changed) `step.updated`/`alert.*` events | M |
| FR-06 | Step becomes DONE only after all `goal` predicates TRUE for K consecutive settled ticks (default 2) | M |
| FR-07 | Red alert only with positive evidence per `docs/ARCHITECTURE.md §6`; otherwise amber/none | M |
| FR-08 | Each alert includes `error_type`, step, message, confidence, ≥1 evidence frame id | M |
| FR-09 | "Check now" forces a tick even if scene is stable | M |
| FR-10 | If SAM/Spark fails or times out, UI shows "verification unavailable" amber, offers manual confirm; session continues | M |
| FR-11 | Finish produces report listing each step: DONE / INCOMPLETE / PROBLEM with timestamps | M |
| FR-12 | Recorded clip can be run through the identical pipeline at 1× real-time or fast mode | M |
| FR-13 | Alert text is generated from templates keyed by `error_type` + step hints; LLM polish optional | M/S |
| FR-14 | Manual override: user can mark a step done/skipped; logged as `manual` | M |
| FR-15 | Per-session model-call budget (default 400 calls) with graceful stop | M |

## 9. Non-functional requirements
| ID | Requirement | Target |
|---|---|---|
| NFR-01 | Tick latency (trigger-settled → events emitted) | p50 ≤ 3 s, p95 ≤ 6 s `[ASSUMPTION]` — **measure in S1; revise via ADR** |
| NFR-02 | Determinism: same observations + config ⇒ identical events | 100 % (property test) |
| NFR-03 | Reproducibility: all tests run offline from cassettes | `make test` needs no network |
| NFR-04 | Resilience: API 429/5xx/timeouts → retry w/ backoff + jitter; never crash session | M |
| NFR-05 | Security/privacy: key server-side; Standard-mode models only; frames stay local | see `docs/SECURITY.md` |
| NFR-06 | Accessibility: state by icon+label+colour; keyboard operable controls | M |
| NFR-07 | Observability: structured logs with `session_id`, `tick_id`, per-model latency | M |
| NFR-08 | Cost guard: per-session call budget; eval runs announce themselves (shared per-team rate limits) | M |
| NFR-09 | Startup: `make setup && make dev` works on a clean machine in ≤ 10 min | M |

## 10. System behaviour (summary — details in `docs/ARCHITECTURE.md`)
Tick = trigger (scene change then settle ≥ 700 ms, or Check-now, or 6 s heartbeat) → best recent frame → SAM calls (unique concepts for active + next step + `hand`) in parallel → geometry in Python → Spark attribute calls (batched crops) only if needed → `Observation` → engine → events → UI. One tick in flight; newer triggers coalesce.

## 11. Technical constraints
- Must use Meta Model API models (`sam-3.1`, `muse-spark-1.3`); Standard mode only. `[FACT]` Rate limits are per **team**: Spark 3 000 RPM/4 M TPM, SAM 3 000 RPM; Contributor variants 150 RPM. `[FACT]` SAM: one noun phrase per request, text output in special-token grammar, boxes+masks; video = file upload (MP4/MOV, H.264/H.265/MPEG-4), not live streaming.
- Software-only trade-offs: single fixed camera; fixed lighting; no depth; fine-grained orientation (LED polarity) may be infeasible from a webcam → gated (G0), not promised.
- Assumptions to test: S1 latency · S2 SAM on small parts · S3 Spark colour classification on tube crops · S4 orientation reading · S5 PDF input · S6 browser capture on both dev machines.

## 12. Success metrics
**Product/eval (measured on frozen held-out test set; targets are goals, not promises — report whatever is measured):**
| Metric | Definition | Target |
|---|---|---|
| Error recall | injected errors with a correct-step red alert within 10 s of visible onset ÷ injected errors | ≥ 0.80 per protocol (stretch 0.90) |
| Type accuracy | of detected errors, share with correct `error_type` | ≥ 0.75 |
| False alarms | red alerts in correct runs ÷ correct runs | ≤ 0.10 |
| Time-to-warning | onset → alert displayed (median / p90) | ≤ 6 s / ≤ 10 s |
| Clean-run pass | correct runs where all steps end green with zero red | ≥ 0.80 |
| Uncertain rate | share of ticks `UNKNOWN`-driven amber | report only |
**Engineering:** `make test` green offline; ≥ 85 % line coverage on `engine/`, `contracts/`; zero secrets in repo.
**Hackathon:** demo ≤ 3 min runs without intervention 5/5 rehearsals; README has architecture diagram, results table, failure case, models-used list.

## 13. Acceptance criteria (feature-level; phase files hold task-level ACs)
| ID | Given / When / Then |
|---|---|
| AC-F01 | Given Protocol A SOP text, when compiled 10×, then ≥ 9 outputs pass schema + lint and all contain the gold object set (fuzzy concept match) |
| AC-F05 | Given a frame with 5 tubes in a rack, when a tick runs, then 5 `tube` detections are returned and colour readings are produced for the queried tubes |
| AC-F06 | Given identical observations, when the engine runs twice, then events are byte-identical |
| AC-F07 | Given a recorded clip where the LED is placed before the resistor, then a `WRONG_ORDER` alert fires on step 2 with evidence, and none fires on a correct clip |
| AC-F08 | Given any session, then every step shows an icon+text status and the UI never shows red for `UNKNOWN` |
| AC-F10 | Given a finished session, then `report.md` and `events.jsonl` exist and `report.md` step statuses match the final engine state |
| AC-F11 | Given a kit missing one required object, preflight lists it as not found with a suggested action |
| AC-F12 | Given the frozen test set, `make eval` reproduces `eval/reports/<tag>/summary.json` and the README table verbatim |
| AC-F13 | Given an `.mp4` clip, when replayed, then the same `events` schema is produced as a live session |
| AC-F15 | Given `CASSETTE=replay`, when tests run with the network disabled, then all pass |

## 14. Risks (top; full table in `docs/RESEARCH.md §6`)
SAM/Spark latency too high · SAM concept sensitivity on small parts · orientation unreadable from webcam · rate-limit contention between two devs and eval runs · over-tuning on test clips · scope too large for ~9 effective days · kickoff is evening IST (Day 1 is short).

## 15. Open questions (resolve by end of Day 1 — owner: both)
1. Official Rules: is a 2-person team allowed in the **Indie** track? Is each teammate required to be an accepted applicant? Which models must/may be used?
2. Does the rule "built during the hackathon" allow pre-kickoff planning docs? (Default: commit docs only after kickoff.)
3. Exact submission deadline in IST (Nov 4, 9:00 PM ET; US DST ends Nov 1 so ET = UTC−5 ⇒ 07:30 IST Nov 5; one aggregator says 06:30 IST — treat 06:30 as the hard limit).
4. Does the team's Meta Model API key have `sam-3.1` + `muse-spark-1.3` access, and is it **one team** for both devs (limits are per team)?
