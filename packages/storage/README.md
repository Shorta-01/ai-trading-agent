# ai-trading-agent-storage

Dit package is een technische storage-foundation voor AI-Trading-Agent.

## Doel van dit package
- SQLAlchemy/Alembic dependencylaag voorbereiden.
- Eén centrale metadata-target voorzien voor toekomstige migraties.
- Veilige database-url redaction helpers voorzien zonder secrets te tonen.

## Bewuste grenzen in deze fase
- Geen tabellen.
- Geen migratie-revisies.
- Geen persistence van setup/portfolio/transacties/suggesties.
- Geen API- of worker-runtime databaseverbinding.
- Domain en portfolio blijven database-vrij.
- `alembic.ini` bevat enkel een placeholder-url, nooit echte secrets.

## Volgende stap (later)
- Eerste schema-migratie toevoegen voor paper setup en audit foundation.

## Task 24: first schema migration foundation
- Eerste schema-tabellen zijn gedefinieerd in SQLAlchemy Core metadata.
- Eerste Alembic migratie-revisie bestaat nu voor paper setup en audit foundation.
- De app gebruikt de database nog niet in runtime (geen API/worker DB-verbinding).
- First-run setup wordt nog niet gepersisteerd.
- Tabellen zijn alleen storage-foundation mappings, zonder businesslogica.
- Geldkolommen gebruiken Numeric (Decimal-compatibel), geen floattypes.
- Paper-only constraints zijn expliciet op schema-niveau vastgelegd.
- `audit_events` is foundation-only; hash-chain/append-only enforcement volgt later.


## Task 24B planned broker sync schema
- De volgende migratie is nu gepland in `packages/storage/docs/broker-sync-schema-plan.md`.
- Geplande tabellen omvatten broker accounts, sync runs, snapshots, reconciliation reports/differences en external broker activities.
- Er bestaan momenteel nog geen broker sync tabellen in de database.
- De volgende migratie zal de geplande tabellen implementeren.
- Er wordt momenteel geen IBKR-data gepersisteerd.

## Task 25A: broker sync schema slice 1
- `broker_accounts` en `broker_sync_runs` bestaan nu in SQLAlchemy Core metadata + Alembic migratie `0002_broker_accounts_and_sync_runs`.
- Dit is bewust alleen de **eerste** broker-sync schema slice.
- De overige 7 broker/reconciliation-tabellen volgen in latere migraties.
- Er wordt nog geen IBKR-data geïmporteerd door de draaiende app.
- Runtime persistence bestaat nog niet: geen repositories, geen API/worker DB-writes.



## Task 25B: broker sync schema slice 2
- `broker_position_snapshots` en `broker_cash_snapshots` bestaan nu in metadata + Alembic migratie `0003_broker_position_and_cash_snapshots`.
- Dit is bewust alleen broker schema slice 2.
- Er wordt nog geen IBKR-data geïmporteerd.
- Er is nog geen runtime persistence, repositorylaag of API/worker DB-writepad.


## Task 25C: broker sync schema slice 3
- `broker_execution_snapshots` en `broker_commission_snapshots` bestaan nu in metadata + Alembic migratie `0004_broker_execution_and_commission_snapshots`.
- Dit zijn uitsluitend imported broker facts tabellen (executions/commissions), geen ordertransmissie.
- Er wordt nog geen IBKR-data geïmporteerd door runtime.
- Er is nog geen runtime persistence, geen repositories, en geen API/worker DB writes.
\n\n## Task 25D update (2026-05-19)\n- Added broker_reconciliation_reports and broker_reconciliation_differences in storage schema slice 4.\n- Scope is status/difference storage only; no reconciliation engine, IBKR integration, runtime persistence, repositories, API/worker DB wiring, or order transmission yet.\n- external_broker_activities remains planned for a later migration.


## Task 25E update (2026-05-19)
- Added `external_broker_activities` schema migration and metadata/export wiring (slice 5).
- Planned broker sync schema foundation is now structurally complete.
- This table stores external broker activity records only.
- No external activity detection engine, no IBKR data import, no runtime persistence, no repositories, no API/worker DB writes, and no order transmission exist yet.
