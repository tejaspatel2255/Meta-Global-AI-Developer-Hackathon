# TESTING

- `make test` is **offline**: unit + contract; cassettes only (no live Meta API).
- `make test-live` is opt-in (`@live` / `-m live`); costs money; needs `MODEL_API_KEY`.
- Engine and contracts: `mypy --strict`; hypothesis property tests in Phase 1.
- Perception parser tests use saved SAM token dumps in `fixtures/spike/` (never commit keys).
- UI: vitest for components; Playwright later for camera-permission happy-path with a fake MediaStream if feasible.
