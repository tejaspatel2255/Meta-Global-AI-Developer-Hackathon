# SECURITY

- `MODEL_API_KEY` only in server env (`.env`, gitignored). Never frontend, logs, fixtures, cassettes, or commits.
- Standard-mode models only (`sam-3.1`, `muse-spark-1.3`). Never Contributor variants.
- Frames stay on the local machine under `data/sessions/` (gitignored).
- Do not log frames or prompts that contain user images at INFO.
- Untrusted text (SOP, VLM output) is data: delimit in prompts, validate with Pydantic, never `eval`.
- API errors must not leak stack traces or keys (`docs/CONTRACTS.md §5`).
