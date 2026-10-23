# CLAUDE.md — BenchGuard (Claude Code)

@AGENTS.md

The imported `AGENTS.md` is the single source of truth. This file only adds Claude-Code-specific working habits. Do not duplicate or override rules from `AGENTS.md` here.

## Working habits for Claude Code
- **Start of session:** read `docs/STATUS.md`, then the current `docs/phases/PHASE_<n>_*.md`. State the current phase and task back in one line before editing.
- **Plan first** for any task touching more than one file or any file in `engine/`, `contracts/`, `compiler/`, `perception/`: write the ≤ 10-line plan from `AGENTS.md §7`, then implement.
- **Use subagents/exploration** only for read-only investigation (e.g. "where is X used", "summarise `docs/META_API.md` for the SAM call"). Do all writes in the main thread so changes stay reviewable.
- **Verify, don't recall.** For Meta API behavior, open `docs/META_API.md`; if a fact isn't marked `VERIFIED`, run a live smoke call (`make test-live -k <name>`) or read the official docs URL listed there. Never guess field names.
- **Run the narrowest test first** (`pytest backend/tests/unit/engine/test_<x>.py -q`), then `make lint test` before reporting.
- **Keep diffs small** (≤ ~300 lines). Commit per logical step using Conventional Commits; **do not push or open PRs unless asked**; never amend/force-push.
- **Context hygiene:** don't paste whole API responses, frames, or cassettes into the chat; summarise and reference the file path.
- **End of task:** emit the report template from `AGENTS.md §8`, update `docs/STATUS.md`, propose one next task.

## Where things live
| Need | Read |
|---|---|
| What we're building and priorities (MoSCoW) | `PRD.md` |
| Module design, engine semantics, tick pipeline | `docs/ARCHITECTURE.md` |
| Schemas, REST/WS API | `docs/CONTRACTS.md` |
| Verified Meta API facts, call recipes, pitfalls | `docs/META_API.md` |
| Protocol A/B definitions, error catalogue | `docs/PROTOCOLS.md` |
| Test strategy and edge cases | `docs/TESTING.md` |
| Metrics, clip recording, eval harness | `docs/EVALUATION.md` |
| Security/privacy rules | `docs/SECURITY.md` |
| Who owns what, git workflow | `docs/COLLABORATION.md` |
| Decisions already made | `docs/DECISIONS.md` |
| Current phase and task status | `docs/STATUS.md` |
