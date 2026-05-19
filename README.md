# Portfolio Outlook Manager

## Doel van het project
Portfolio Outlook Manager is een professionele **AI-ondersteunde paper portfolio research- en beslissingsomgeving**. Het systeem helpt een gebruiker bij het analyseren van toegelaten ETF's, aandelen en valuta's, en geeft duidelijke actiesuggesties in eenvoudige Nederlandse taal.

## Belangrijke waarschuwing: versie 1 is paper-only
- Versie 1 werkt **uitsluitend** met papergeld.
- Geen live trading.
- Geen real-money orders.
- Geen broker execution.
- Geen automatische orderplaatsing.

## Kernprincipes
- **Complexe backend, eenvoudige Nederlandse frontend.**
- **Python berekent, AI legt uit.**
- AI is onderzoek/uitleg, niet uitvoering.
- Risicoregels en audittrail zijn leidend.

## High-level architectuur (foundation)
- **Frontend (apps/web):** eenvoudige Nederlandse UI met hulpteksten.
- **API-backend (apps/api):** FastAPI shell met health-endpoints en basisconfiguratie.
- **Workers (apps/worker):** placeholder workerproces met veilige paper-only statusfunctie.
- **Pakketten (packages/*):** placeholder domeinmodules (risk, portfolio, tax, audit, ai, enz.).
- **Nieuw:** `packages/domain` bevat gedeelde, gevalideerde domeincontracten (data-shapes, geen tradinglogica).
- **Nieuw:** `packages/portfolio` bevat paper accounting helperberekeningen (puur, deterministisch, Decimal-only).
- **Opslag:** PostgreSQL placeholder via Docker Compose; nog geen businessmodellen/migraties.
- **Infra (infra/docker):** Docker Compose-gedreven development setup en portabiliteit.

## Lokale development (technische skeleton)

### API
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn portfolio_outlook_api.main:app --reload --app-dir src
```

### Worker
```bash
cd apps/worker
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python src/portfolio_outlook_worker/main.py
```

### Web
```bash
cd apps/web
npm install
npm run dev
```

### Docker Compose
```bash
cd infra/docker
docker compose up --build
```

## No-live-trading principe
De applicatie mag in versie 1 geen echte broker-orders uitvoeren, geen live-accounts aansturen en geen real-money transacties automatiseren.

## Product-governance documentatie
- Version 1 scope register: `docs/product/version-1-scope-register.md`

## Eenvoudige Nederlandse UI-principe
Alle hoofdschermen, labels, waarschuwingen en acties moeten begrijpelijk zijn voor niet-experts. Elke veldwaarde krijgt eenvoudige Nederlandse helptekst/tooltip.

- Nieuw in de paper-only foundation: contracten en berekeningshelpers voor **Mijn termijnrekeningen**.

- Nieuw: backend-foundation voor een paper-only asset capability registry met allowed/watch-only/blocked regels.
\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).
\n## Scheduler and background job planning\nContracts define planning only: plan -> eligibility -> skip/block/run status -> audit trace. Suggestion jobs require gezonde services en verse data; geen job voert trades uit. Zware AI/research taken horen in queue of externe worker, niet als onbeperkte Raspberry Pi scan.

## Task 16 foundation update
Settings/secrets metadata and OpenAI usage-cost budget contracts are added as domain-only foundations without real API calls or secret storage.

## Task 17 update
De API bevat nu read-only, Nederlandstalig voorbereide status- en instellingen-samenvattingsendpoints voor de toekomstige web-UI, zonder secrets of externe runtime-calls.

- Nieuw: de webapp bevat nu een modern Nederlandstalig dashboard als veilige paper-only foundation.
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.


## Database planning status (Task 21)
- AI-Trading-Agent kiest **PostgreSQL** als geplande primaire gestructureerde database.
- **Alembic** is gekozen als gepland migratiekader voor een latere implementatiefase.
- Database-implementatie is nog niet gestart; de app bewaart nog geen paper-portefeuilledata.


## PostgreSQL development service (Task 22)
- Local PostgreSQL development service is available via `infra/docker/docker-compose.yml`.
- The application still does not persist setup, portfolio, cash, transactions, or settings yet.
- No setup/portfolio data is saved in the app runtime at this stage.

## Storage dependency and migration skeleton (Task 23)
- Nieuw package `packages/storage` met SQLAlchemy/Alembic skeleton.
- Nog geen tabellen, nog geen migraties en nog geen persistence in app-runtime.

## Storage schema status (Task 24)
- Eerste storage schema-migratie bestaat nu voor paper setup + audit foundation.
- De applicatie persisteert nog steeds geen portfolio- of setupdata in runtime.
\n\n## Task 24A update\nIBKR wordt na koppeling de bron van waarheid voor brokerfeiten; lokale data blijft een spiegel voor analyse en audit. Er is nog geen echte IBKR-integratie in deze versie.


## Task 24B update
- Broker sync schema is now planned in detail for the next storage migration.
- No IBKR broker data is stored yet in the current application runtime.
- IBKR integration is not implemented yet.

## Task 25A update
- Eerste broker sync schema slice is toegevoegd in storage (`broker_accounts`, `broker_sync_runs`).
- Er is nog geen IBKR-integratie of runtime persistence actief.



## Task 25B update
- Broker snapshot schema slice 2 toegevoegd: `broker_position_snapshots` en `broker_cash_snapshots`.
- Er is nog geen IBKR-integratie, geen runtime persistence en geen app DB-writepad actief.


- Task 25C update: broker execution/commission snapshot schema foundation exists (slice 3), imported facts only; no runtime IBKR sync wiring, no order transmission, reconciliation tables remain future work.
\n\n## Task 25D update (2026-05-19)\n- Added broker_reconciliation_reports and broker_reconciliation_differences in storage schema slice 4.\n- Scope is status/difference storage only; no reconciliation engine, IBKR integration, runtime persistence, repositories, API/worker DB wiring, or order transmission yet.\n- external_broker_activities remains planned for a later migration.


## Task 25E update (2026-05-19)
- Added `external_broker_activities` in storage schema slice 5; the planned broker sync/reconciliation schema foundation is now structurally complete.
- No IBKR integration, runtime persistence, external activity detection engine, or order transmission exists yet.

## Storage repository contracts update (Task 26)
- Broker sync/reconciliation storage repository interfaces are now defined in the storage package.
- This is contract-only: no concrete persistence implementation, no API/worker wiring, and no runtime database writes yet.


## Task 27 update
- Migration readiness contracts bestaan nu in het storage package met verwachte revisies `0001` t/m `0006`.
- Dit is alleen offline readiness-inventaris; er is nog geen echte database-readiness check.
- Runtime persistence bestaat nog niet en writes blijven geblokkeerd.


## Task 28 update
- Online Alembic migration readiness check bestaat nu in het storage package via een expliciet aangeleverde SQLAlchemy `Connection`.
- Deze check leest alleen `alembic_version`, maakt geen app-engine/sessie aan en leest geen environment-variabelen.
- Er is nog geen app DB-wiring of runtime persistence in API/worker.

## Update Task 29
SQLAlchemy opslag-repository skelet toegevoegd met expliciete `Connection` + migration readiness report. Geen app-engine/session, geen DATABASE_URL/env wiring, geen API/worker runtime persistence, geen IBKR-import.

## Task 30 update
- API endpoint `/storage/status` gebruikt nu storage migration readiness contracts uit `packages/storage`.
- Status meldt expliciet dat de database niet verbonden is en dat runtime writes geblokkeerd blijven.
- Endpoint bevat nu migration readiness velden inclusief verwachte laatste revisie `0006`.

## Task 47 update (2026-05-19)
- IBKR integration foundation now includes official research notes and ADR 0003 for adapter-first architecture.
- Added typed internal broker adapter contracts with Decimal-only financial fields; no credentials, no real IBKR calls, and no order submission.
- Added read-only endpoint `GET /broker/ibkr/status` with Dutch placeholder status; orders remain blocked until future account-mode verification.
