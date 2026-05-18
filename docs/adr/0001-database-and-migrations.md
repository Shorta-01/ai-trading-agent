# ADR 0001: Database and migration direction

- Status: Accepted
- Date: 2026-05-18

## Context
AI-Trading-Agent is in a paper-only foundation phase, but it already requires strict auditability, deterministic calculations, clear risk boundaries, and future-safe persistence. The project must support concurrent backend services, scheduled jobs, structured research records, and point-in-time reconstruction. The platform must stay portable across Linux ARM64 and Linux AMD64 (including Raspberry Pi 5 deployments).

Storage is not implemented yet. First-run setup and paper cash are still preview-only and are not persisted.

## Decision
1. **Primary structured database:** PostgreSQL.
2. **Future time-series direction:** a TimescaleDB-compatible approach, introduced later on top of PostgreSQL-compatible tables.
3. **Planned migration framework:** Alembic (to be added in a later implementation PR).
4. **Repository architecture:** explicit typed repository interfaces. Domain and portfolio business logic stays in domain/portfolio packages, not in SQL models, migrations, or API routes.
5. **First persistence target:** first-run paper setup, initial paper cash account, and first audit event.
6. **Secrets policy:** no secrets in regular database tables; only secret references/status metadata may be persisted.
7. **Trust boundary:** persistence is not trusted until backup and restore testing is implemented and passing.
8. **Scope boundary for this PR:** no database implementation, no migration scripts, and no database dependencies are added.

## Consequences
- The team can align docs, API status messaging, and roadmap around one storage direction.
- SQLite is not used as the main application database.
- We keep portability and avoid Raspberry Pi-specific application logic.
- We can add migrations and repositories later without moving financial rules into persistence code.
- Read-only API/UI can clearly communicate “planned but not active” storage.

## Alternatives considered
- **SQLite as main DB:** rejected for this system scope (concurrency, audit rigor, background workload evolution, and operational backup/restore expectations).
- **JSON/local files only:** rejected due to weak schema governance, difficult concurrent writes, and limited operational traceability.
- **Direct SQL only (without migration framework):** rejected because schema evolution and deployment consistency become error-prone over time.
- **ORM-first design as source of truth:** rejected because business rules must remain explicit in domain/portfolio logic, not hidden in persistence models.
- **PostgreSQL + Alembic:** chosen as the most practical, portable, and maintainable path for incremental implementation.

## Future follow-up tasks
1. Add local PostgreSQL development service and environment-based connection wiring.
2. Add database dependency layer and repository interfaces.
3. Add Alembic skeleton and first migration.
4. Persist first-run setup, initial paper cash account, and initial audit event.
5. Add restore-tested backup process and trusted-backup status checks.
6. Add storage-driven API responses and dashboard status updates without fake data.
