# Architectuur

## Backend/frontend scheiding
- Frontend: eenvoudige Nederlandse weergave, hulpteksten, duidelijke acties.
- Backend: data-inname, validatie, scoring, risicocontrole, audit, explainability.

## Professionele beslisstack
1. Universe Selection
2. Research and Signal Generation
3. Portfolio Construction
4. Risk Management
5. Execution Simulation
6. Reconciliation and Accounting
7. Tax and Compliance
8. Performance Attribution
9. Self-Learning (voorstel-gedreven, niet autonoom)

## Hoofd-backendmodules (doelarchitectuur)
Gedocumenteerde enginefamilies: universe, data quality, portfolio, risk, decision, execution simulation, tax/compliance, performance, audit, self-learning.

## Hoofd-frontendsecties
Dashboard, Prestaties, Actiesuggesties, Portefeuille, Volglijst, Kansen/Waarschuwingen, Transactiegeschiedenis, Asset Detail, Belgische fiscaliteit/compliance, Instellingen, Audit/leerinzichten.

## Versie 1 grenzen
- Paper-only.
- Geen live trading.
- Geen broker execution.
- Geen IBKR-verbinding in deze fase.

## Paper-only guardrail
Alle architectuurkeuzes ondersteunen eerst controleerbare paper workflows met volledige audittrail en zonder real-money uitvoering.
\n## Update: execution/approval/research contracts\n- Paper-first is full workflow (niet prototype) met verplichte goedkeuring per koop/verkoop.\n- Execution modes: internal_paper, ibkr_paper, ibkr_live_read_only, ibkr_live_manual, blocked_auto.\n- Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked.\n- IBKR paper is toekomstig execution target na setup en goedkeuring.\n- Broker-neutrale flow: suggestion -> approval -> execution_intent -> execution adapter.\n- IBKR metadata blijft in reference contracts (geen live API-calls).\n- AI research output is alleen onderzoek/uitleg; nooit approval/execution override.\n- Source/reference + hashes + archiefkoppeling vormen auditlijn: source -> report -> suggestion -> approval -> order -> transaction.\n- Geen persistence, geen DB-modellen, geen API/worker/frontend wijzigingen in deze stap.\n

## Task 11 data-source strategie
- Domeincontracten toegevoegd voor bronbeleid, betrouwbaarheid, gebruiksrechten, versheid en failure policy.
- IBKR blijft enige toekomstige broker/execution route; geen runtime integraties toegevoegd.
- Publieke nieuws- en websitebronnen zijn standaard niet geschikt voor suggestion eligibility.
- Geen data kwaliteit of traceerbaarheid betekent geen advies/suggestie.

\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).
\n## Scheduler and background job planning\nContracts define planning only: plan -> eligibility -> skip/block/run status -> audit trace. Suggestion jobs require gezonde services en verse data; geen job voert trades uit. Zware AI/research taken horen in queue of externe worker, niet als onbeperkte Raspberry Pi scan.

## Task 14 update
Data-quality gate en suggestion eligibility foundations toegevoegd. Deze stap maakt geen aanbevelingen en geen execution.
\n## Task 15 update\nAction suggestion engine foundation toegevoegd: candidate -> capability/data-quality gates -> eligibility -> risk placeholder -> cost/tax placeholder -> suggestion draft. Dit genereert nog geen echte aanbevelingen, geen orders en geen automatische uitvoering.

## Task 16 foundation update
Settings/secrets metadata and OpenAI usage-cost budget contracts are added as domain-only foundations without real API calls or secret storage.

## Read-only status/settings API foundation
- Domeincontracten blijven de bron voor regels en boundaries.
- De API exposeert veilige, read-only samenvattingen voor status en instellingen.
- De web-UI consumeert later deze samenvattingen voor statuskaarten en instellingenoverzicht.
- Er is in deze stap geen runtime-integratie (geen broker, geen OpenAI, geen scheduler, geen worker-activatie).
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.


## Database and repository architecture plan (Task 21)

### Domain package
- Validates data and policy boundaries.
- Owns business contracts and safety rules.
- Contains no database imports.

### Portfolio package
- Owns accounting/portfolio calculations and guardrails.
- Contains no database-specific logic.

### API package
- Exposes read-only and later write-safe endpoints.
- Will call repository services later for persistence orchestration.
- Must not contain business calculations.
- Must not expose secrets.

### Future persistence module (planned, not implemented)
- Typed repository interfaces.
- PostgreSQL adapters.
- Alembic migrations.
- Schema mapping between persistence and domain contracts.

No persistence module is implemented in this PR.


## PostgreSQL infrastructure boundary (Task 22)
- PostgreSQL service is infrastructure, not business logic.
- Domain and portfolio packages remain database-free.
- API/worker persistence layers must not contain financial rules.
- A future repository layer will handle persistence mapping between storage and domain contracts.

## Task 23: storage package boundary
- `packages/storage` is toegevoegd voor toekomstige migraties en repository-adapters.
- `packages/domain` en `packages/portfolio` blijven database-vrij.
- API/worker zullen later repository-services aanroepen, niet rechtstreeks SQL in routes/jobs.
- Migraties en Alembic-config mogen geen businesslogica bevatten.

## Task 24 storage boundary update
- Storage-schema bestaat nu als foundation, terwijl domain/portfolio de bron van businessregels blijven.
- Database-schema is bedoeld om later gevalideerde feiten op te slaan, niet om berekeningslogica te dragen.
- API en worker zijn nog niet aan PostgreSQL gekoppeld.
- Repository-interfaces en persistence orchestration volgen in volgende taken.
\n\n## Task 24A update\nIBKR wordt na koppeling de bron van waarheid voor brokerfeiten; lokale data blijft een spiegel voor analyse en audit. Er is nog geen echte IBKR-integratie in deze versie.


## Task 24B broker sync storage flow
Planned end-to-end storage flow once broker sync implementation starts:
1. IBKR import source
2. Raw source reference (later phase)
3. Normalized broker snapshot records
4. Reconciliation report and differences
5. Local mirror update flow (later phase)
6. Audit linkage
7. Suggestion allowed/blocked based on reconciliation status

This PR only designs the schema and does not implement migration, persistence runtime, or IBKR connectivity.

## Task 25A storage foundation update
- Het storage schema bevat nu de eerste broker-sync foundation (`broker_accounts`, `broker_sync_runs`).
- API en worker zijn nog niet aan database writes gekoppeld.
- Repository-interfaces/adapters voor broker snapshots volgen later.



## Task 25B architectuurupdate
- Storage-schema foundation bevat nu broker account/sync run/position snapshot/cash snapshot tabellen.
- API en worker zijn nog niet aan DB-writes gekoppeld.
- Repository-implementaties volgen later.


- Task 25C update: broker execution/commission snapshot schema foundation exists (slice 3), imported facts only; no runtime IBKR sync wiring, no order transmission, reconciliation tables remain future work.
\n\n## Task 25D update (2026-05-19)\n- Added broker_reconciliation_reports and broker_reconciliation_differences in storage schema slice 4.\n- Scope is status/difference storage only; no reconciliation engine, IBKR integration, runtime persistence, repositories, API/worker DB wiring, or order transmission yet.\n- external_broker_activities remains planned for a later migration.
