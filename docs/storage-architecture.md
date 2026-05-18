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
\n## Update: execution/approval/research contracts\n- Paper-first is full workflow (niet prototype) met verplichte goedkeuring per koop/verkoop.\n- Execution modes: internal_paper, ibkr_paper, ibkr_live_read_only, ibkr_live_manual, blocked_auto.\n- Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked.\n- IBKR paper is toekomstig execution target na setup en goedkeuring.\n- Broker-neutrale flow: suggestion -> approval -> execution_intent -> execution adapter.\n- IBKR metadata blijft in reference contracts (geen live API-calls).\n- AI research output is alleen onderzoek/uitleg; nooit approval/execution override.\n- Source/reference + hashes + archiefkoppeling vormen auditlijn: source -> report -> suggestion -> approval -> order -> transaction.\n- Geen persistence, geen DB-modellen, geen API/worker/frontend wijzigingen in deze stap.\n

## Task 11 data-source strategie
- Domeincontracten toegevoegd voor bronbeleid, betrouwbaarheid, gebruiksrechten, versheid en failure policy.
- IBKR blijft enige toekomstige broker/execution route; geen runtime integraties toegevoegd.
- Publieke nieuws- en websitebronnen zijn standaard niet geschikt voor suggestion eligibility.
- Geen data kwaliteit of traceerbaarheid betekent geen advies/suggestie.

\n## Scheduler and background job planning\nContracts define planning only: plan -> eligibility -> skip/block/run status -> audit trace. Suggestion jobs require gezonde services en verse data; geen job voert trades uit. Zware AI/research taken horen in queue of externe worker, niet als onbeperkte Raspberry Pi scan.

## Task 14 update
Data-quality gate en suggestion eligibility foundations toegevoegd. Deze stap maakt geen aanbevelingen en geen execution.
\n## Task 15 update\nAction suggestion engine foundation toegevoegd: candidate -> capability/data-quality gates -> eligibility -> risk placeholder -> cost/tax placeholder -> suggestion draft. Dit genereert nog geen echte aanbevelingen, geen orders en geen automatische uitvoering.

## Task 16 foundation update
Settings/secrets metadata and OpenAI usage-cost budget contracts are added as domain-only foundations without real API calls or secret storage.


## Selected storage direction (Task 21)
- Primary structured storage direction: **PostgreSQL first**.
- Time-series expansion direction: **TimescaleDB-compatible later**, after baseline PostgreSQL tables exist.
- Planned migrations framework: **Alembic later** (not implemented in this PR).

## Repository layer boundaries
- Domain and portfolio packages keep business rules and financial calculations.
- Repository interfaces must be explicit and typed.
- SQL mapping, adapters, and migrations may not become the source of truth for domain rules.
- API routes stay orchestration-only and must not contain business calculations.

## First entities to persist
1. First-run paper setup configuration.
2. Initial paper cash account state.
3. Initial audit event linked to that setup.

Market data, AI research archives, and broader time-series persistence are later phases.

## Secret handling
- Secrets are never stored as plain values in normal application tables.
- Only secret references and status metadata may be persisted.

## Backup, restore, and trust readiness
- Backup encryption is mandatory once persistence exists.
- Restore testing is mandatory before persistence is marked trusted.
- “Backup exists” alone is insufficient; restore validation must pass.

## Point-in-time reconstruction
- Stored records must remain suitable for point-in-time reconstruction of decisions and audits.
- As-of and audit linkage fields remain required for later schema design.

## What is still not implemented
- Storage is still not implemented.
- No setup is saved yet.
- The API may show storage as planned, but not connected.
- Migrations are not available yet.
- Restore testing is required before storage can be considered trusted.


## PostgreSQL dev container status (Task 22)
- PostgreSQL development container exists for local infrastructure preparation.
- It is infrastructure-only in this phase.
- No schema or migrations exist yet.
- No app persistence is active yet.

Future implementation order:
1. database dependency layer
2. Alembic skeleton
3. first migration
4. repository interfaces
5. first-run setup persistence
6. audit event persistence
7. backup/restore workflow

## Task 23: storage dependency layer en Alembic skeleton
- Nieuw package `packages/storage` toegevoegd als duidelijke storage-boundary.
- SQLAlchemy metadata-target en Alembic skeleton zijn aanwezig.
- Er is nog geen schema, geen tabellen en geen migratie-revisie.
- Er is nog geen persistence van setup/portfolio/transacties/suggesties.
- Database-URL labels moeten secrets redigeren (geen wachtwoorden tonen).
- Volgende stap: eerste schema-migratie voor paper setup + audit foundation.
