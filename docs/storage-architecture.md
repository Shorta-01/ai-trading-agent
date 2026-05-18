# Storage Architecture

## Opslaglagen
1. **PostgreSQL/TimescaleDB** voor gestructureerde data, tijdreeksen, portfolio, transacties, instellingen, suggesties en jobs.
2. **Immutable raw archive** voor originele bronbestanden/snapshots.
3. **Research & audit archive** voor AI-input/output, referenties, model/promptversies en besliscontext.

## Auditlog
Append-only of hash-ready auditlog voor controleerbaarheid, herleidbaarheid en tamper-evident evolutie.

## Point-in-time regel
Beslissingen en backtests moeten point-in-time correct zijn; geen toekomstige informatie in historische beslissingen.

## Verplichte tijdvelden
Records ondersteunen o.a. as_of_date, valid_from, valid_to, published_at, retrieved_at, used_in_run_id, source_snapshot_id.

## Dataflow (target)
1) Fetch
2) Immutable raw opslag
3) Source record
4) Data quality checks
5) Normalisatie naar DB
6) Python berekening
7) Controlled AI research package
8) Schema-validatie AI output
9) Decision/risk combinatie
10) Suggestiecreatie
11) Risk approve/block
12) UI-publicatie
13) Actie/executie logging
14) Outcome tracking

## Backup en restore
Backups zijn verplicht, maar pas vertrouwd na periodieke restore-tests.

## Migratiepad Raspberry Pi -> mini PC
Infra blijft platform-onafhankelijk via Docker Compose, env-files, named volumes en gestandaardiseerde data-export/import zonder code rewrite.
