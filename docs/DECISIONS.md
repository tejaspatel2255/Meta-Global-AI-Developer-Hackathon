# DECISIONS (ADRs)

Architecture in `docs/ARCHITECTURE.md` is frozen. New ADRs go here and require **both** humans.

## ADR-0001 — Structure-first verifier (accepted, planning)
Models localise and read attributes; Python engine owns statuses and alerts. Positive-evidence alarming only.

## ADR-0002 — Stack (accepted, planning)
Python 3.11 + FastAPI, React + Vite + TS, Meta Model API via `openai` SDK `base_url=https://api.meta.ai/v1`. No extra dependencies without a one-line justification and human approval.
