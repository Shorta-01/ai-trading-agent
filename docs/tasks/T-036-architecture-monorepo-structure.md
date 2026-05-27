```yaml
id: T-036
title: Write architecture review doc — 01 monorepo structure
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/architecture-review/01-monorepo-structure.md` does not exist (verified). Every code site is already cited in T-001 … T-010 reality docs:
  - T-010 `stub-packages.md` — 6 README-only stub packages (`ai`, `analytics`, `audit`, `data_providers`, `risk`, `tax`).
  - T-001 / T-002 / T-003 — `packages/domain` / `packages/portfolio` / `packages/storage` (3 real Python packages with their own `pyproject.toml`).
  - T-006 / T-007 — `apps/api` + `apps/worker` (the two backend apps).
  - T-008 / T-009 — `apps/web` (the only TypeScript surface).
  - T-009 — root infra/CI inventory (`Makefile`, `.github/workflows/ci.yml`, `infra/docker/`).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the verdict-driven architecture review of the monorepo structure.
  - `01-monorepo-structure.md` — 8-question verdict-driven assessment: (1) apps/packages layout, (2) workspace-manager choice (none), (3) 6 stub packages, (4) Makefile orchestration vs task-runner, (5) per-app CI jobs, (6) per-package dev tool config duplication, (7) frontend isolation, (8) Docker/infra layout. Each question gets current implementation + state-of-the-art alternative + verdict (state-of-the-art / acceptable / outdated / risky) + perf implication + concrete improvement.
- **Step 3 (one-line change):** write one verdict-driven architecture review of the monorepo structure.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; 8 architectural questions enumerated; verdict format applied to each (current + alternative + verdict + perf + improvement); current implementation cites file paths; verdicts include at least 2 "outdated" or "risky" calls (to demonstrate critique-mode not pat-on-back); the 6-stub-package architectural debt explicitly verdicted; recommendations deferred to Track 1c per the README mandate; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — Python stack details (T-037 next), Frontend stack details (T-038 future), data + storage architecture (T-039 future), testing + CI deep dive (T-040 future). T-036 covers structure-of-the-repo, not internal architecture.

## Goal

Produce one verdict-driven architecture review of the monorepo structure — 8 architectural choices assessed with the locked 5-part verdict format (current implementation + state-of-the-art alternative + verdict + performance implication + concrete improvement). Focus on the meta-question "is the way the repo is laid out fit for purpose, scalable, maintainable?". Recommendations go in Track 1c gap analysis; T-036 captures verdicts, not fixes.

## Context

`depends_on:` T-001 … T-010. The reality docs documented WHAT exists; T-036 opens Track 1b which asks IS IT GOOD. Track 1b consists of 7 focused review docs + 1 summary (T-043). T-036 covers the structural choice; T-037-T-042 cover language stacks + data + testing + perf + security; T-043 synthesises.

## Touch scope

Create:
- `docs/architecture-review/01-monorepo-structure.md`

Read: T-001-T-010 reality docs + root configs (`pyproject.toml`, `Makefile`, `.github/workflows/ci.yml`).

## Acceptance criteria

- [ ] Output file exists at `docs/architecture-review/01-monorepo-structure.md`.
- [ ] 8 architectural choices enumerated (apps/packages layout, no workspace manager, 6 stub packages, Makefile orchestration, per-app CI jobs, per-package dev tool config, frontend isolation, Docker layout).
- [ ] Verdict format applied to each (current + alternative + verdict + perf + improvement).
- [ ] Verdicts span at least 3 of the 4 ratings — at least 2 "outdated" or "risky" calls to demonstrate critique-mode.
- [ ] 6-stub-package architectural debt explicitly verdicted (citing T-010).
- [ ] Each "current implementation" section cites at least one file path.
- [ ] No source modification.
- [ ] Recommendations deferred to Track 1c per the README mandate.

## Out of scope

- Python stack details (T-037 — next).
- Frontend stack details (T-038 — future).
- Data + storage architecture (T-039 — future).
- Testing + CI deep dive (T-040 — future).
- Performance + scale (T-041 — future).
- Security + ops (T-042 — future).
- Summary (T-043 — written LAST after T-036-T-042).
- Concrete fixes (Track 1c — gap analysis).

## Verification

- File exists.
- 8 architectural choices each have the full 5-part verdict.
- Verdicts span multiple ratings (no pat-on-back).
- File:line citations in current-implementation sections.

## Notes

T-036 opens Track 1b Architecture Review — a different doctrinal mode than Track 1a Reality Docs. Track 1a says "what IS"; Track 1b says "is what IS good?". The format is verdict-driven, opinionated, structured. Each verdict must defensible by citing reality docs. Recommendations live in Track 1c (gap analysis), not here. Discipline: critique without prescribing.
