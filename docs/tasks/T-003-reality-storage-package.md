```yaml
id: T-003
title: Write reality doc for `packages/storage` and its Alembic chain
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: (set on push)
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the touch scope is one new file under `docs/reality/components/`; it does not exist yet. The source modules to read (8 files under `packages/storage/src/ai_trading_agent_storage/`, ~15.6k lines total, with `repository_contracts.py` at ~4.3k lines and `sql_repositories.py` at ~6.6k lines) plus the 53-migration chain in `packages/storage/alembic/versions/` plus `alembic.ini` and `env.py` are inventoried below; a single subagent is launched to read them in full and return structured content.
- **Step 2 (one-line per touched file):** the one target file does not exist; it will hold the reality doc covering: storage modules (`__init__`, `metadata`, `settings`, `alembic_helpers`, `connection_provider`, `migration_readiness`, `repository_contracts`, `sql_repositories`) + Alembic chain overview (count, naming convention, slice categories, bookends).
- **Step 3 (one-line change):** write one cited reality doc describing what the existing `packages/storage` package exports + how its 53-migration Alembic chain is shaped, with `path/to/file.py:NNN` cites on every claim.
- **Step 4 (criteria measurable):** yes — six acceptance criteria are observable (file exists at locked path; "Modules covered" lists the 8 storage modules; "Alembic chain" cites count/convention/latest revision + role of `migration_readiness.py` + ADR 0001 + `docs/storage-architecture.md`; per-Sql-repo catalogue; Decimal + CHECK policies cited; Open questions section present).
- **Step 5 (out-of-scope does not block goal):** confirmed. Per-migration deep dive is excluded; no coverage of `apps/api` or `apps/worker` wiring (those are T-005 / T-007); no source or migration file modified.

## Goal

Produce `docs/reality/components/storage-package-and-migrations.md`, a single reality doc covering the storage package and the 54-migration Alembic chain.

## Context

`packages/storage` is the SQLAlchemy repos + connection + migration_readiness layer. 8 source files plus 54 Alembic migrations. The migration chain is too large to deep-dive per migration — the file gives an overview (count, naming convention, latest revision, migration-readiness gating) and per-migration detail only where a migration introduces a locked schema change cited elsewhere in reality docs. `depends_on:` —.

## Touch scope

Create:
- `docs/reality/components/storage-package-and-migrations.md`

Read (no modification): all `packages/storage/src/ai_trading_agent_storage/*.py`, plus `packages/storage/alembic/` for migration overview, plus existing `docs/storage-architecture.md` and ADR `0001-database-and-migrations.md` as intent input.

## Acceptance criteria

- [ ] Output file exists with the locked filename.
- [ ] Section "Modules covered" lists the 8 storage modules.
- [ ] Section "Alembic chain" gives: total migration count, naming convention, latest revision identifier, role of `migration_readiness.py` in the chain, and citations to ADR 0001 + `docs/storage-architecture.md`.
- [ ] Repository class catalogue: one bullet per public Sql* repo with file:line and a one-line description.
- [ ] Decimal-precision and CHECK-constraint policies cited (this package is the persistence-side enforcement).
- [ ] "Open questions / uncertainty" present.

## Out of scope

- Per-migration deep dive (54 migrations); only flagged migrations introduce a paragraph.
- No coverage of how `apps/api` or `apps/worker` invoke the repos (covered by T-005, T-006, T-007).
- No source / migration file modification.

## Verification

- File exists at the locked path.
- Latest Alembic revision identifier matches `packages/storage/alembic/versions/` head.

## Notes

Modules in scope: `sql_repositories`, `repository_contracts`, `connection_provider`, `migration_readiness`, `settings`, `metadata`, `alembic_helpers`, `__init__`.

Existing intent references: `docs/storage-architecture.md`, `docs/adr/0001-database-and-migrations.md`.
