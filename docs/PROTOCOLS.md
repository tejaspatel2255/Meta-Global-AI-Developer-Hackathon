# PROTOCOLS.md — Protocol A & B (the only two we claim)

Concept phrases, thresholds and the orientation error are **assumptions** until spikes S2–S4 (`docs/META_API.md §5`). Gold IR files live in `protocols/*.gold.ir.json` (created in Phase 1) and are the compiler's reference and the engine's integration fixtures. Do not add a third protocol.

## 0. Shared setup rules (state them in the README as limitations)
- **Fixed camera** on tripod/stand, top-down or ~60° elevated, 1280×720, framing the whole work area; do not move it during a session.
- **Diffuse, constant lighting**; matte white surface; no strong glare. Re-run preflight if light changes.
- **One operator**, hands leave the frame (or the relevant objects) for **≥ 2 s after each action** ("protocol discipline" — lets the trigger settle). Stated honestly in the demo.
- Kit parts laid **left of the work area** in view (preflight checks them).
- Everything is non-hazardous (water, food colouring, low-voltage-free breadboard parts).

---
## Protocol A — "LED indicator on a breadboard"
**Kit:** half-size breadboard · 1 resistor · 1 red 5 mm LED · 1 **capacitor** (distractor) · 1 red jumper wire · 1 black jumper wire. (No battery: wires are plugged in but not powered — nothing to verify electrically.)
**SOP text (fed to the compiler; keep verbatim in `protocols/protocol_a.sop.md`):**
```
Title: LED indicator on a breadboard
1. Insert the resistor into the breadboard.
2. Insert the red LED into the breadboard.
3. Plug the red jumper wire into the breadboard on the left.
4. Plug the black jumper wire into the breadboard on the right.
Notes: Use the resistor, not the capacitor. Insert parts in the order given. Red wire must be left of black wire.
```
### Gold IR outline (objects → concept → expected_count)
`breadboard`→"breadboard"(1) · `resistor`→"resistor"(1) · `led`→"red led"(1) · `capacitor`→"capacitor"(1, distractor, declared only in signatures) · `red_wire`→"red jumper wire"(1) · `black_wire`→"black jumper wire"(1) · (`hand` implicit)
| Step | Goals | Invariants | Error signatures / notes |
|---|---|---|---|
| s1 Resistor | `relation resistor inside breadboard` | `present breadboard` | **WRONG_OBJECT**: `relation capacitor inside breadboard` TRUE |
| s2 LED | `relation led inside breadboard` | `present breadboard` | *(gated, G0)* `attribute led polarity` `allowed:["correct"] pending:[] category:orientation gate: relation led inside breadboard` |
| s3 Red wire | `relation red_wire inside breadboard` | — | — |
| s4 Black wire | `relation black_wire inside breadboard` | `order_along [red_wire, black_wire] x` (**invariant**) | swapped wires ⇒ invariant FALSE with both present ⇒ **WRONG_POSITION** (A2) |
### Error catalogue (injection scripts for eval)
| ID | Error | How the operator injects it | Expected alert | Gate |
|---|---|---|---|---|
| A-E1 | Wrong component | Insert the capacitor instead of the resistor at s1 | `WRONG_OBJECT` on s1 | — |
| A-E2 | Wrong order | Insert LED **before** resistor | `WRONG_ORDER` on s1 (`related_step_id`=s2) | — |
| A-E3 | Wires swapped | Plug red wire on the right, black on the left | `WRONG_POSITION` on s4 | — |
| A-E4 | LED reversed | Insert LED with flat edge on the wrong side (use a visible marker dot on the cathode rim; disclose in README) | `WRONG_ORIENTATION` on s2 | **G0**: ≥ 80 % agreement on 20 calibration crops (S4) else drop and say so |
Minimum error types claimed: A-E1, A-E2, A-E3 (3). A-E4 only if G0 passes.
### Assumptions to test
SAM finds `resistor`/`red led` at 1280×720 on a breadboard (S2) · `inside` via boxes is robust (box of a part overlaps breadboard box ≥ 0.8 of its own area) · wire colour concepts separate red from black wires (S2).

---
## Protocol B — "Colour dilution in a labelled rack"
**Kit:** rack with **5 clear tubes** (or small clear vials) positioned left→right and labelled **A B C D E** with tape · stock **A** red water, **B** blue, **C** yellow (food colouring) · **D, E** empty · dropper/pipette or pour. Tubes **stay in their rack positions** (assumption; the slot mapping depends on it — state in README).
**SOP text (`protocols/protocol_b.sop.md`):**
```
Title: Two-colour mixing in a labelled rack
1. Transfer stock A (red) into tube D.
2. Transfer stock B (blue) into tube D.
3. Transfer stock C (yellow) into tube E.
4. Transfer stock B (blue) into tube E.
Notes: Tubes A–E stand left to right in the rack. Pause for 2 seconds after each transfer with hands out of view. Tube D should end purple and tube E green.
```
### Gold IR outline
Objects `tube_a … tube_e` → concept `"test tube"`, `expected_count 5`, `slot {axis:x, index:0..4, of:5}`.
Attribute `liquid_color`, question "What colour is the liquid in this tube?", closed set `[clear, red, blue, yellow, purple, green]` (+ reserved `unclear`, `other` — **never evidence**).
| Step | Goals | Invariants |
|---|---|---|
| s1 A→D | `tube_d` `allowed[red] pending[clear]` | `tube_e allowed[clear]` |
| s2 B→D | `tube_d` `allowed[purple] pending[red]` | `tube_e allowed[clear]` |
| s3 C→E | `tube_e` `allowed[yellow] pending[clear]` | `tube_d allowed[purple]` |
| s4 B→E | `tube_e` `allowed[green] pending[yellow]` | `tube_d allowed[purple]` |
All attributes: `category: state`. Every error leaves a **colour signature** — that is the design principle (we verify end-states, not pouring actions).
### Error catalogue
| ID | Error | Injection | Expected alert |
|---|---|---|---|
| B-E1 | Wrong destination | s1: pour A into **E** instead of D | `WRONG_STATE` on s1 (tube E not clear — A1 invariant) |
| B-E2 | Wrong order | After s1, do s3 (C→E) before s2 | `WRONG_ORDER` on s2 (`related`=s3) |
| B-E3 | Skipped step | After s1 go straight to s3 and s4, never s2 | `WRONG_ORDER` → reclassified `SKIPPED_STEP` after `skip_reclass_ms` |
| B-E4 | Mixed in wrong sequence | s1: pour B (blue) into D first | `WRONG_STATE` on s1 (D reads blue ∉ allowed ∪ pending) |
Minimum error types claimed: `WRONG_STATE`, `WRONG_ORDER`, `SKIPPED_STEP` (3).
### Non-goals / honest limits
**Volumes are not verified.** Pouring/pipetting actions are not recognised — only resulting colours. Colour readings need good light (S3). Identical-looking mixed colours (e.g. orange vs yellow) are excluded by dye choice.

---
## Calibration shot lists (Phase 0, spikes S2–S4) — save under `fixtures/spike/`
- **A (≥ 30 frames):** empty board + kit; each part in/out of the board; LED correct/reversed ×10 (marker dot visible); wires correct/swapped; hand in frame; 2 lighting levels.
- **B (≥ 30 crops, ≥ 5 per colour):** each colour in tubes D/E at 3 fill levels and 2 lighting levels; clear/empty; purple/green mixes at mid-fill.
- Name files `<protocol>_<what>_<nn>.jpg`; keep a `manifest.csv` with ground truth (`file, label`). Used by S3/S4 accuracy and later as dev fixtures.

## Dev vs test clips
Dev clips (tuning): 3 correct + 3 error per protocol, recorded Day 3–4. Test clips (frozen headline): recorded **after** `eval-freeze-v1` (Day 7). See `docs/EVALUATION.md`.
