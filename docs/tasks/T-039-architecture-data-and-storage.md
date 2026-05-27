```yaml
id: T-039
title: Write architecture review doc — 04 data and storage
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/architecture-review/04-data-and-storage.md` does not exist (verified). Every code site is already cited in T-003 + T-037 reality docs:
  - T-003 `storage-package-and-migrations.md` — full reality of `packages/storage/` (8 modules, 53 migrations, tri-defense safety-boolean + per-asset hash-chain).
  - T-037 §5 — SQLAlchemy Core 88 `Table(` already verdicted acceptable.
  - T-037 §6 — `psycopg[binary]` v3 already verdicted acceptable.
  - `packages/storage/src/ai_trading_agent_storage/metadata.py` — 3116 LOC, 88 tables, 47 JSON columns, 33 indexes, 58 FKs, 89 MONEY_NUMERIC.
  - `packages/storage/src/ai_trading_agent_storage/sql_repositories.py` — 6617 LOC, 53 repository classes.
  - `packages/storage/alembic/versions/` — 53 migrations, linear chain.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the verdict-driven architecture review of data + storage.
  - `04-data-and-storage.md` — 8-question verdict-driven assessment: (1) PostgreSQL + SQLite-for-tests dual stack, (2) 88 tables in single 3116-LOC `metadata.py`, (3) 53-migration linear Alembic chain, (4) 47 JSON columns (denormalisation level), (5) Decimal-as-string + `MONEY_NUMERIC` discipline, (6) Repository pattern with 53 hand-coded classes / 6617 LOC, (7) No connection pooling beyond SQLAlchemy default, (8) Single-database deployment (no read replicas, no caching layer).
- **Step 3 (one-line change):** write one verdict-driven architecture review of the data + storage layer.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; 8 architectural choices enumerated; 5-part verdict format applied to each; verdicts span at least 3 ratings; the Decimal-as-string discipline verdicted state-of-the-art (rare moment of high praise for the data layer); the 47 JSON columns + 88-tables-in-one-file verdict; recommendations deferred to Track 1c; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — monorepo (T-036 merged), Python stack (T-037 merged), frontend (T-038 merged), testing+CI deep dive (T-040 next), performance+scale (T-041 future).

## Goal

Produce one verdict-driven architecture review of the data + storage layer — the PostgreSQL + SQLite split, the 88-table schema, the 53-migration Alembic chain, the Decimal discipline, the repository pattern. The dominant story: solid fundamentals (Decimal-as-string is rigorous; append-only audit pattern is doctrine-compliant; per-asset hash chains are forensic-grade) but a few structural choices that scale poorly: single 3116-LOC `metadata.py`, 6617-LOC `sql_repositories.py`, no caching layer.

## Context

`depends_on:` T-001 … T-010. T-003 covered the storage reality in depth; T-037 §5-§6 already verdicted the SQLAlchemy + psycopg choices. T-039 zooms into data architecture specifically: schema shape, migration discipline, scale ceilings.

## Touch scope

Create:
- `docs/architecture-review/04-data-and-storage.md`

Read: T-003 + T-037 reality docs + `metadata.py` + `sql_repositories.py` + `alembic/versions/` directory listing.

## Acceptance criteria

- [ ] Output file exists at `docs/architecture-review/04-data-and-storage.md`.
- [ ] 8 architectural choices enumerated.
- [ ] 5-part verdict format applied to each.
- [ ] Verdicts span at least 3 ratings.
- [ ] Decimal-as-string discipline verdicted (state-of-the-art).
- [ ] 88-tables-in-single-file pattern verdicted.
- [ ] 47 JSON columns documented + verdicted.
- [ ] Recommendations deferred to Track 1c.
- [ ] No source modification.

## Out of scope

- Monorepo (T-036 — merged).
- Python stack (T-037 — merged; SQLAlchemy + psycopg already verdicted there).
- Frontend (T-038 — merged).
- Testing + CI deep dive (T-040 — next).
- Performance + scale (T-041 — future; though §11 has perf observations).
- Security + ops (T-042 — future).
- Summary (T-043 — last).
- Concrete fixes (Track 1c).

## Verification

- File exists.
- 8 choices × 5-part verdict.
- Multi-rating distribution.
- Decimal discipline verdicted.
- Single-file metadata pattern verdicted.

## Notes

T-039 is the 4th of 8 Track 1b architecture review docs. The data layer is the strongest part of the codebase by far — Decimal-as-string is enforced, audit tables are append-only with UNIQUE constraints, hash chains exist for forensic reconstruction. The criticisms are structural: 3116 LOC in one `metadata.py` becomes hard to navigate; 6617 LOC in one `sql_repositories.py` is even worse; single Postgres deployment with no caching layer is a scale ceiling. Phase 1c may want to split the schema files OR adopt a caching tier.
