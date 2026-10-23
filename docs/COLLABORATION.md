# COLLABORATION.md — Prit (Dev A) & Tejas (Dev B)

Default split below is **derived from the architecture's dependency graph**, not from anyone's strengths (unknown to this doc). Swap workstreams in the Day-1 kickoff if skills differ — record the swap in `docs/DECISIONS.md` and update `CODEOWNERS`.

## 1. Workstreams & independence
| WS | Scope | Default owner | Can start without the other? |
|---|---|---|---|
| **WS-E** Engine & compiler | `contracts/` (co-own), `geometry/`, `engine/`, `compiler/`, `export/`, `runner/`, `api/` | **Dev A (Prit)** | Yes — works on fixtures (`Observation` JSON), no camera/API needed for engine |
| **WS-P** Perception | `meta_client/`, `perception/` (frame source, trigger, SAM, crops, attributes, cassettes, preflight) | **Dev B (Tejas)** | Yes — produces `Observation`s; tested with real frames + cassettes |
| **WS-U** UI | `frontend/` | **Dev B** (after P2) | Yes — against a **mock WS server** emitting fixture events from `fixtures/events/*.jsonl` |
| **WS-V** Validation | `eval/` harness+metrics (A), clip recording/labelling (both; B performs, A records/annotates and vice-versa) | shared | harness yes (fake clips), clips need hardware kit |
Balance check: A ≈ 7.5 pd, B ≈ 7 pd, shared ≈ 2 pd (see phase files). If A finishes early → takes UI polish/report HTML; if B early → takes Protocol B IR + ablation.

### Interfaces that decouple the streams (frozen end of Day 2 = **IC-1**)
1. `contracts/` Pydantic models + generated JSON Schema/TS types.
2. `PerceptionRequest → detections → AttributeQuery → readings → Observation` (`docs/CONTRACTS.md §3`).
3. WS/REST API (`§5–6`) + event stream fixtures.
4. Gold IR files `protocols/*.gold.ir.json`.
Anything crossing these requires a joint decision (ADR).

## 2. Directory ownership (`.github/CODEOWNERS`)
```
/backend/benchguard/contracts/      @pritpatel2412 @tejaspatel2255
/docs/                              @pritpatel2412 @tejaspatel2255
/backend/benchguard/geometry/       @pritpatel2412
/backend/benchguard/engine/         @pritpatel2412
/backend/benchguard/compiler/       @pritpatel2412
/backend/benchguard/runner/         @pritpatel2412
/backend/benchguard/api/            @pritpatel2412
/backend/benchguard/export/         @pritpatel2412
/backend/benchguard/meta_client/    @tejaspatel2255
/backend/benchguard/perception/     @tejaspatel2255
/frontend/                          @tejaspatel2255
/eval/                              @pritpatel2412 @tejaspatel2255
/protocols/ /fixtures/              @pritpatel2412 @tejaspatel2255
```
Editing someone else's directory: small PR + tag the owner; never push to their branch.

## 3. Git workflow
- **Trunk-based**: `main` always green and demo-able. Short-lived branches `feat/<ws>-<topic>` (`feat/p-sam-fanout`, `fix/e-order-reclass`), ≤ 1 day old when merged.
- **Conventional Commits** (see `AGENTS.md §5`). Squash-merge PRs; PR title = commit message.
- **PR rules:** ≤ ~300 changed lines; description = AGENTS report template (what/tests/ACs/not-verified); linked phase task id; CI (`make lint test`) green; **1 approval from the other dev** (docs-only and fixtures-only may self-merge after 24 h silence on Days 8–10 only).
- **Review SLA:** ≤ 2 h during working hours; reviewer checks: AC evidence, R1–R17 compliance, contract drift, no secrets.
- **Contracts/IR/alarm semantics/thresholds-as-policy:** ADR entry first, both approve, then code.
- **Tags:** `ic-1…ic-5` at integration checkpoints; `eval-freeze-v1` (never move); `submission-v1`.
- **Never** force-push `main`; **never** rewrite shared branches; rebase your own branch on `main` daily.
- **Merge-conflict prevention:** ownership by directory; generated files (`frontend/src/contracts/*`) regenerated via `make schemas` (never hand-edited — resolve conflicts by regenerating); `docs/STATUS.md` edited by the task's author in the same PR (append-only table rows to avoid conflicts).
- **Hackathon provenance:** open the repo, then commit docs **after** Oct 26 12:00 ET kickoff unless Official Rules say planning docs may predate it (open question PRD §15). Everything else is written after kickoff.

## 4. Integration checkpoints
| IC | When | What must work | Both verify |
|---|---|---|---|
| IC-1 | end Day 2 | contracts + fixtures frozen; gold IRs lint; mock WS server; S1–S4 results & **gate G0 decision** | `make test` green; tag `ic-1` |
| IC-2 | end Day 4 | recorded dev clip → perception (cassette-recorded) → engine → alerts offline (no UI) | replay-E2E test |
| IC-3 | end Day 6 | **live** Protocol A end-to-end in browser (camera → UI alerts) | 3 consecutive correct runs + 1 error run by hand |
| IC-4 | end Day 7 | Protocol B live; thresholds frozen; tag `eval-freeze-v1` | both run a full session |
| IC-5 | Day 9 18:00 IST | **code freeze**; README, results, demo assets; `submission-v1` | fresh-clone setup in ≤ 10 min on both machines |
Each IC: 20-min joint session; failures become top-priority tasks; update `STATUS.md`.

## 5. Testing responsibilities
Authors write/run tests for their code. Reviewer re-runs the narrowest relevant test. Shared: replay-E2E (A writes harness, B supplies clips/cassettes), Playwright E2E (B), eval harness (A), clip recording/annotation (both; second annotator spot-checks). Acceptance criteria are shared (phase files + PRD §13) — no one self-certifies a gate alone: **gates G0–G3 need both sign-offs** in `STATUS.md`.

## 6. Communication & cadence (IST; confirm Tejas's time zone on Day 1)
- Daily 15-min sync (start of day) + 10-min handoff note at end of day in `STATUS.md` ("blockers / next").
- One shared channel; announce: eval runs, API-heavy runs, contract changes, tag creation, camera/lighting changes during recording.
- Shared Meta API team (limits per team): one key each; **never** run eval and a demo rehearsal simultaneously.
- Decision protocol: disagreement ⇒ 10-minute timebox, write both options in `DECISIONS.md`, pick by PRD priority + feasibility; the cut ladder (PRD §6.1) breaks ties.
- Working agent hygiene: each dev's coding agents obey `AGENTS.md`; agent-authored PRs get the same review; agents must not push/merge.

## 7. Calendar (Day = hackathon day; dates 2026; kickoff Mon Oct 26 ≈ 21:30 IST)
| Day | Date | Dev A (Prit) | Dev B (Tejas) | Joint |
|---|---|---|---|---|
| 1 | Mon Oct 26 | repo+CI scaffold, `make` targets | Meta API key/team, S1/S2 smoke calls | read Official Rules; resolve PRD §15 |
| 2 | Tue Oct 27 | P1 compiler, gold IRs | P2 frame source/trigger/SAM client | S1–S6, **G0**, **IC-1** |
| 3 | Wed Oct 28 | P1 done; P3 engine core | P2 fan-out, parser, cassettes | dev clips A |
| 4 | Thu Oct 29 | P3 engine rules | P2 attributes/crops/preflight | **IC-2**, dev clips B |
| 5 | Fri Oct 30 | P3 done; P4 runner+API | P4 UI scaffold on mock | |
| 6 | Sat Oct 31 | P7 export; eval harness | P4 UI live wiring | **IC-3**; P5 starts |
| 7 | Sun Nov 1 | P5 Protocol B IR/tuning | P5 hardening | **IC-4**, freeze, record test clips |
| 8 | Mon Nov 2 | P6 run eval, ablations | P6 failure analysis, fixes (v2) | backup demo video |
| 9 | Tue Nov 3 | P7 polish, README results | P7 UI polish, demo video | **IC-5** freeze 18:00 |
| 10 | Wed Nov 4 | final checks | final checks | **submit ≤ 20:00 IST** |
Hard deadline Nov 4 21:00 ET = Nov 5 07:30 IST (treat **06:30 IST** as the limit until Rules confirm).
