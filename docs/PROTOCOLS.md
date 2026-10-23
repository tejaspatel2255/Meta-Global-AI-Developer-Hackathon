# PROTOCOLS

Hard scope: two protocols only (`PRD.md §5.1`).

## Protocol A — LED on breadboard
Place resistor, then LED, then battery/wires, in order. Intended errors: wrong component (distractor), wrong order, plus **one** of {wrong orientation, wrong position} chosen after gate G0 (spike S4). Gold IR lives in `fixtures/protocols/protocol_a.json` once compiled and linted.

## Protocol B — Colour dilution in labelled rack
Five tubes A–E, coloured water, four transfers. Every injected error must leave a **visible colour** end-state. Errors: wrong destination (wrong state), wrong order, skipped step. Gold IR: `fixtures/protocols/protocol_b.json`.

SOP source text for both: `fixtures/protocols/*.sop.txt` (added with gold IR in Phase 3).
