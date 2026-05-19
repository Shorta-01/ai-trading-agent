# Roadmap

## Milestone 1: Trustworthy paper core
Fundament voor paper portfolio, audittrail, risicohandhaving en betrouwbare datastromen.

## Milestone 2: AI explanation and research layer
Gecontroleerde AI-uitleglaag met schema-validatie en strikte policy-afbakening.

## Milestone 3: Discovery and monitoring
Uitbreiding met discovery- en intraday-monitoringmodi.

## Milestone 4: Backtesting and performance evaluation
Backtesting, walk-forward evaluatie, performance attribution en calibratie.

## Milestone 5: IBKR paper integration (later)
Later pas broker-koppeling voor papercontext; live uitvoering blijft buiten v1.

## Expliciet niet in versie 1
- Geen live trading.
- Geen real-money execution.
- Geen broker order-routing.
- Geen automatische plaatsing van echte orders.

## Toegevoegd binnen paper foundation
- Ondersteuning voor een aparte paper asset-zone: **Mijn termijnrekeningen** (contracten + pure berekeningshelpers).
- API-endpoints, database-opslag en frontend-flow voor termijnrekeningen blijven expliciet future work.

## Capability roadmap (nieuw)
- Capabilities inbouwen in paper order creation en transaction-guardrails.
- Capabilities blootstellen via API-contracten.
- Toegestaan/alleen opvolgen/geblokkeerd zichtbaar maken in de Nederlandse UI.
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

## Nieuwe vervolgstappen na Task 17
- Koppel status-API aan echte runtime health-checks.
- Koppel settings-API aan persistente instellingenopslag.
- Koppel OpenAI-verbruiksendpoint aan echte usage/cost-collector.
- Bouw IBKR paper-statuschecker.
- Bouw moderne Nederlandstalige Instellingen-UI.
- Bouw modern Nederlandstalig Systeemstatus-dashboard.

## Task 18 update
- Moderne Nederlandstalige dashboard foundation opgeleverd in de webapp.
- Veilige read-only secties toegevoegd voor systeemstatus, instellingen, AI-verbruik en koppelingen.
- Lege, veilige placeholders toegevoegd voor actiesuggesties en portefeuille zonder nepdata.

## Vervolg na Task 18
- Koppel dashboardstatus aan echte runtime health-signalen.
- Bouw veilige instellingenformulieren (zonder secrets in plain text).
- Voeg first-run paper-portefeuille setup-UI toe.
- Bouw echte portefeuilleweergave met alleen gevalideerde data.
- Voeg actiesuggestie-grid toe zodra gates en data actief zijn.
- Voeg grafieken pas toe als echte data beschikbaar is.
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.


## Storage planning update (Task 21)

### Reeds afgerond
- Storage readiness contracts.
- Storage status endpoint.
- Database/migration decision (PostgreSQL + Alembic planning).

### Eerstvolgende taken
- Add PostgreSQL development service.
- Add database dependency layer.
- Add Alembic migration skeleton.
- Add first schema migration.
- Add repository interfaces.
- Persist first-run setup.
- Persist paper cash account.
- Persist audit event.
- Expose saved portfolio status API.
- Show saved paper cash in Dutch dashboard.


## Storage roadmap update (Task 22)

### Reeds afgerond
- PostgreSQL development service foundation (Docker Compose + healthcheck + local volume).

### Eerstvolgende taken
- database dependency layer
- Alembic migration skeleton
- first schema migration
- repository interfaces
- persist first-run setup
- persist paper cash account
- persist audit event
- storage backup/restore scripts
- restore test workflow

## Task 23 status
- ✅ Database dependency layer en Alembic skeleton toegevoegd.

## Volgende storage taken
1. Eerste schema-migratie voor paper setup + audit foundation.
2. Repository-interfaces toevoegen voor storage mapping.
3. Persistente opslag voor first-run paper setup toevoegen.
4. Database-readiness check toevoegen voor runtimestatus.
5. Backup- en restore-scripts met restore-verificatie toevoegen.

## Task 24 status
- ✅ Eerste schema-migratie voor paper setup en audit foundation afgerond.

## Volgende storage-taken
1. Repository-interfaces voor first-run setup toevoegen.
2. Database-readiness check tegen migratiestatus toevoegen.
3. First-run setup persisteren.
4. Initiële paper cash account persisteren.
5. Setup audit event persisteren.
6. Dashboard status met opgeslagen portfolioinformatie tonen (zonder fake data).
\n\n## Task 24A update\nIBKR wordt na koppeling de bron van waarheid voor brokerfeiten; lokale data blijft een spiegel voor analyse en audit. Er is nog geen echte IBKR-integratie in deze versie.


## Task 24B status
### Reeds afgerond
- IBKR source-of-truth en reconciliation architectuurbeslissing vastgelegd.
- Broker sync schema planning en migration design vastgelegd.

### Eerstvolgende taken
1. Broker sync schema migration implementeren.
2. Repository interfaces voor broker snapshots en reconciliation records toevoegen.
3. IBKR settings/status velden toevoegen (zonder secrets op te slaan).
4. IBKR bootstrap preview flow toevoegen.
5. Broker snapshot import adapter skeleton toevoegen.
6. Reconciliation engine foundation toevoegen.

## Task 25A status
- ✅ Broker account + broker sync run schema migratie afgerond (`0002`).

## Volgende broker-storage taken
1. Broker snapshot schema migratie.
2. Broker reconciliation schema migratie.
3. Repository-interfaces voor broker snapshots/reconciliation.
4. IBKR settings/status velden (zonder secrets).
5. IBKR bootstrap preview.



## Task 25B status
- ✅ Broker position and cash snapshot schema migration afgerond.

## Volgende broker taken
1. Broker execution en commission snapshot schema migration.
2. Broker reconciliation schema migration.
3. Repository-interfaces voor broker snapshots.
4. IBKR settings/status velden.
5. IBKR bootstrap preview.


- Task 25C update: broker execution/commission snapshot schema foundation exists (slice 3), imported facts only; no runtime IBKR sync wiring, no order transmission, reconciliation tables remain future work.
\n\n## Task 25D update (2026-05-19)\n- Added broker_reconciliation_reports and broker_reconciliation_differences in storage schema slice 4.\n- Scope is status/difference storage only; no reconciliation engine, IBKR integration, runtime persistence, repositories, API/worker DB wiring, or order transmission yet.\n- external_broker_activities remains planned for a later migration.


## Task 25E update (2026-05-19)
Done now:
- External broker activities schema migration (0006).
- Broker sync schema foundation complete.

Next:
- Repository interfaces for broker snapshots and reconciliation.
- Database readiness checks for migrations.
- IBKR settings/status fields.
- IBKR bootstrap preview.
- Broker snapshot import adapter skeleton.
- Reconciliation engine foundation.
- External broker activity detection logic.

## Task 26 afgerond
- Repository interfaces voor broker sync en reconciliation storage boundary toegevoegd.

## Next
- Database readiness check voor migrations.
- SQLAlchemy repository implementation skeleton.
- IBKR settings/status velden.
- IBKR bootstrap preview.
- Broker snapshot import adapter skeleton.
- Reconciliation engine foundation.


## Task 27 status
- ✅ Database migration readiness contracts en offline migration inventory afgerond.

## Volgende storage taken
1. Online database readiness check tegen Alembic version table.
2. SQLAlchemy repository implementation skeleton.
3. App storage configuratievelden.
4. API storage readiness endpoint op basis van storage package.
5. IBKR settings/status velden.
6. IBKR bootstrap preview.


## Task 28 status
- ✅ Online database readiness check tegen Alembic version table afgerond.

## Volgende taken na Task 28
1. SQLAlchemy repository implementation skeleton.
2. App storage configuratievelden.
3. API storage readiness endpoint op basis van storage package.
4. IBKR settings/status velden.
5. IBKR bootstrap preview.
6. Broker snapshot import adapter skeleton.
7. Reconciliation engine foundation.

## Update Task 29
SQLAlchemy opslag-repository skelet toegevoegd met expliciete `Connection` + migration readiness report. Geen app-engine/session, geen DATABASE_URL/env wiring, geen API/worker runtime persistence, geen IBKR-import.
