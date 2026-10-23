# EVALUATION.md — How we produce numbers judges can trust

Goal: a small, honest, reproducible evaluation. Headline numbers come **only** from held-out test clips recorded **after** the freeze. Never fabricate or round up; report failures (AGENTS R13).

## 1. Dataset
| Split | Purpose | Protocol A | Protocol B | Recorded |
|---|---|---|---|---|
| **dev** | tune prompts, thresholds, concept phrases | 3 correct + 3 error | 3 correct + 3 error | Day 3–4 |
| **test** | frozen headline | 10 correct + 5 each of A-E1, A-E2, A-E3 (+5 A-E4 only if G0 passed) | 8 correct + 4 each of B-E1, B-E2, B-E3 (+4 B-E4 optional) | Day 7, **after** `eval-freeze-v1` |
| **confirm** *(Could)* | check v2 fixes on fresh data | 4 correct + 4 error | 4 correct + 4 error | Day 8 |
**Minimum viable eval** (if behind): ≥ 10 correct + ≥ 10 error clips per protocol, 3 error types each. Say so in the README.
**Clip spec:** MP4 (H.264), 1280×720, 30 fps, tripod, hands+workspace only (**no faces**), 45–120 s, one run per clip, operator follows protocol discipline (`PROTOCOLS.md §0`). Name `A-C-007.mp4` (correct) / `A-E2-003.mp4` (error type). One injected error per error clip; correct runs must be genuinely correct. Vary lighting slightly and operator hand speed across clips (document in `manifest`).
**Storage:** clips are large → not in git. Host on a release asset/Drive; commit `eval/manifest.json` (`clip_id, sha256, bytes, split, protocol, notes`) and `eval/labels/*.json`.

## 2. Labels (`eval/labels/<clip_id>.json`)
```json
{"clip_id":"A-E2-003","protocol":"A","split":"test","kind":"error",
 "injected":[{"error_type":"WRONG_ORDER","step_id":"s1","related_step_id":"s2","onset_ms":14200}],
 "notes":"LED inserted first"}
```
Correct clips: `"kind":"correct","injected":[]`.
**Onset definition:** the first video timestamp where the wrong state is visibly established and the hand has begun leaving (e.g. capacitor seated in board; LED seated before resistor; wrong tube coloured). For `WRONG_ORDER`/`SKIPPED_STEP`, `step_id` = the step that **should** have been done; `related_step_id` = the step that was done out of order (SKIPPED: none).
**Annotation QA:** both devs annotate independently on ≥ 10 clips; onset disagreement > 1.5 s or type disagreement ⇒ resolve and re-label; report agreement in README appendix.

## 3. Metrics (per protocol and pooled; always with n and 95 % Wilson CI)
| Metric | Definition |
|---|---|
| **Detected** | ≥ 1 `alert.raised` on an error clip with `step_id` == injected `step_id` (or `related_step_id` for order errors) and `onset_ms ≤ alert.t_ms ≤ onset_ms + 10 000`, evaluated in **real-time replay** |
| **Error recall** | Detected ÷ injected errors |
| **Type accuracy** | detected alerts whose `error_type` == injected type ÷ Detected (`WRONG_ORDER` accepted as correct for `SKIPPED_STEP` only if reclass hasn't occurred by clip end — report separately) |
| **False-alarm rate** | correct clips with ≥ 1 red alert ÷ correct clips; also alerts per correct clip |
| **Spurious alerts on error clips** | alerts not matching the injected error (wrong step/type/time) per error clip |
| **Time-to-warning** | `alert.t_ms − onset_ms` for detected errors; median, p90 (n shown); includes trigger-settle delay + model latency |
| **Clean-run pass** | correct clips ending with every step DONE and zero red alerts ÷ correct clips |
| **Uncertain rate** | amber-ticks ÷ ticks (descriptive) |
| **Tick latency** | p50/p95 of `latency_ms.total`, and per model |
| **Cost** | total calls and $ from `n_calls`/pricing (descriptive) |
Wilson 95 % interval for `k/n`: `centre=(p+z²/2n)/(1+z²/n)`, `half=z·sqrt(p(1−p)/n+z²/4n²)/(1+z²/n)`, `z=1.96` (implement + unit-test in `eval/stats.py`; e.g. 17/20 → [0.64, 0.95]).

## 4. Freeze discipline (anti-leakage)
1. Tune only on **dev** clips. 2. When Phase 5 is done: set `config/*.yaml`, prompts, gold IR, concept phrases; commit; `git tag eval-freeze-v1`; record config hash in `eval/reports/v1/config.sha256`. 3. Only then record **test** clips. 4. Run the headline eval **once** on the frozen tag: this is **v1**. 5. Failure analysis may produce fixes → tag `v2`; re-run on the same test set and report v2 **separately labelled "tuned after inspecting test failures (optimistic)"**; prefer the **confirm** set for an unbiased v2. 6. README headline table = v1 (and confirm if available).

## 5. Harness (`eval/`)
```
python -m eval.run --protocol A|B|all --split dev|test|confirm --mode realtime|fast \
                   --concurrency 2 --out eval/reports/<tag>          # make eval
python -m eval.report --in eval/reports/<tag>                        # make eval-report (offline)
python -m eval.ablate --in eval/reports/<tag>                        # engine variants over saved observations (offline)
```
- Runs use the **gold IR** (it stands for the human-reviewed IR, F-02). Compiler quality is reported **separately** (`phases/PHASE_1…` P1-T06); never present eval numbers as covering the compiler.
- Uses **the production path**: `FrameSource(clip)` → trigger → perception → runner → engine (AC-F13). `realtime` paces frames at wall-clock (headline latency/time-to-warning); `fast` uses frame timestamps and charges measured model latency to a virtual clock (regression only; label as approximation).
- Outputs: `per_clip.csv`, `summary.json` (all metrics + CIs), `RESULTS.md` (README-ready table), `observations/<clip>.jsonl`, `events/<clip>.jsonl`, `failures/<clip>/` (evidence frames + overlay + alert JSON).
- **Rate limits are per team:** announce eval runs in the team chat, `--concurrency ≤ 2`, never run while the other dev is demoing. Budget: ≈ 50 clips × ≈ 40 ticks × ≈ 5 calls ≈ 10 000 calls (≈ $25–40 at published prices; verify with `n_calls`).
- Determinism: `eval.report`/`eval.ablate` read saved JSONL only (no API).

## 6. Ablations (cheap, offline — **Should**)
Re-run the **engine** over saved `observations.jsonl` with variants and report FA/recall deltas:
| Variant | Change |
|---|---|
| V0 (shipped) | positive-evidence alarming, K=2, occlusion + settle gates |
| V1 naive | alarm when a goal is FALSE for K ticks (no positive-evidence rule) — expect many false alarms |
| V2 no debounce | K=1 |
| V3 no occlusion gate | ignore `hand` |
| V4 geometry-only | drop attribute readings (UNKNOWN) |
These quantify design choices D2/D3 without extra API cost.

## 7. Failure analysis (required deliverable)
For every missed error and false alarm tag a cause: `perception_miss | vlm_misread | trigger_missed | protocol_discipline | engine_rule | annotation | api_error`. Produce a table (counts per cause) and pick **one representative failure** for the README: what happened, evidence frame, root cause, what we'd fix. Honest limitations paragraph is mandatory.

## 8. README results block (template — numbers only from `summary.json`)
```
| Protocol | Clips (correct / error) | Error recall (95% CI) | False-alarm rate (95% CI) | Time-to-warning median / p90 | Clean-run pass |
|---|---|---|---|---|---|
| A | n / n | k/n (lo–hi) | k/n (lo–hi) | x s / y s | k/n |
| B | … |
Tick latency p50/p95: x / y s. Models: sam-3.1, muse-spark-1.3. Frozen tag: eval-freeze-v1. Limitations: fixed camera & lighting, protocol discipline (2 s pauses), 2 protocols only.
```
