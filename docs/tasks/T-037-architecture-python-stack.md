```yaml
id: T-037
title: Write architecture review doc — 02 Python stack
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/482
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/architecture-review/02-python-stack.md` does not exist (verified). Every code site is already cited in T-001 … T-010 reality docs + T-036:
  - T-001 / T-002 — Pydantic v2 usage; portfolio + domain models.
  - T-003 — SQLAlchemy Core usage (88 `Table(` declarations, 0 ORM `Mapped[]`).
  - T-004 — `ibapi==9.81.1.post1` exact pin.
  - T-005 / T-006 — FastAPI 179 routes; sync handlers (0 async).
  - T-007 — APScheduler in worker.
  - T-023 — anthropic SDK direct import.
  - T-036 §6 — per-package tool config duplication (already verdicted outdated).
  - `apps/api/pyproject.toml`, `apps/worker/pyproject.toml`, `packages/{domain,portfolio,storage}/pyproject.toml`.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the verdict-driven architecture review of the Python stack.
  - `02-python-stack.md` — 8-question verdict-driven assessment: (1) Python 3.12 floor, (2) FastAPI + sync-route pattern, (3) AsyncIO essentially unused, (4) Pydantic v2 + Settings, (5) SQLAlchemy 2.0 Core (not ORM), (6) `psycopg[binary]` v3, (7) `ibapi==9.81.1.post1` exact pin, (8) APScheduler choice. Each question gets current + alternative + verdict + perf + improvement direction.
- **Step 3 (one-line change):** write one verdict-driven architecture review of the Python stack.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; 8 architectural questions enumerated; 5-part verdict format applied to each; verdicts span multiple ratings; sync-route-on-async-framework pattern explicitly verdicted; ibapi pin + maintenance status surfaced; mypy --strict universal coverage noted as state-of-the-art; recommendations deferred to Track 1c; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — monorepo structure (T-036 — merged sibling), frontend stack (T-038 — next), data + storage internals (T-039 — future).

## Goal

Produce one verdict-driven architecture review of the Python stack — language version, web framework, async runtime, validation library, ORM/Core choice, database driver, IBKR adapter, scheduler. 8 architectural choices assessed with the 5-part verdict format. The dominant story: a sync-Python codebase running on an async-first framework (FastAPI) with no async database driver — works fine at single-user scale, becomes a perf wall above ~100 RPS.

## Context

`depends_on:` T-001 … T-010. Reality docs documented WHAT exists; T-037 verdicts the Python language + library choices specifically. T-036 covered structure; T-037 covers language stack; T-038-T-042 will cover the rest.

## Touch scope

Create:
- `docs/architecture-review/02-python-stack.md`

Read: T-001-T-010 reality docs + `apps/api/pyproject.toml` + `apps/worker/pyproject.toml` + `packages/*/pyproject.toml`.

## Acceptance criteria

- [ ] Output file exists at `docs/architecture-review/02-python-stack.md`.
- [ ] 8 architectural choices enumerated (Python 3.12, FastAPI sync routes, AsyncIO usage, Pydantic v2, SQLAlchemy Core, psycopg v3, ibapi 9.81.1.post1, APScheduler).
- [ ] 5-part verdict format applied to each.
- [ ] Verdicts span at least 3 ratings.
- [ ] Sync-route-on-async-framework pattern explicitly verdicted (Pattern, not just "Sync vs Async").
- [ ] `ibapi==9.81.1.post1` exact pin + maintenance status surfaced.
- [ ] `mypy --strict` universal coverage acknowledged as state-of-the-art.
- [ ] No source modification.

## Out of scope

- Monorepo structure (T-036 — merged sibling).
- Frontend stack (T-038 — next).
- Data + storage architecture (T-039 — future).
- Testing + CI deep dive (T-040 — future).
- Performance + scale (T-041 — future; though §11 has perf observations).
- Security + ops (T-042 — future).
- Summary (T-043 — last).
- Concrete fixes (Track 1c).

## Verification

- File exists.
- 8 choices × 5-part verdict.
- Multi-rating distribution.
- Sync-route pattern surfaced as a verdicted choice.
- ibapi pin + maintenance status noted.

## Notes

T-037 is the 2nd of 8 Track 1b architecture review docs. The biggest cross-cutting pattern in the Python stack is **sync-Python on async framework**: 179 FastAPI routes with zero `async def`. The system is doing the right things (Python 3.12, Pydantic v2, SQLAlchemy 2.0 Core, mypy --strict) but with an inconsistent async story. Phase 1c will need to decide whether to commit to async (migrate handlers + add async DB driver) or commit to sync (consider WSGI alternatives like Flask + Gunicorn).
