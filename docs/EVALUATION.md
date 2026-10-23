# EVALUATION

Headline numbers come only from committed artifacts under `eval/reports/<tag>/` (R13).

- Same pipeline for live and recorded clips (`FrameSource`).
- Freeze tag `eval-freeze-v1` before the held-out run.
- Report Wilson 95% CIs; show one failure case.
- `make eval` must reproduce `summary.json` and the README table verbatim.

Phase 6 implements the harness. Do not invent metrics before then.
