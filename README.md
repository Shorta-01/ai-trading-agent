# AI Trading Agent

> **Top-level doctrine:** `docs/intent/_trading-system-doctrine.md` (locked 2026-05-26; adoption record: `docs/decisions/0002-trading-system-doctrine.md`).
> Deze README is samenvattend; bij conflict wint de doctrine.

## Doel van het project
AI Trading Agent is een **volledig handelssysteem**. Het analyseert markten, genereert orderssuggesties en stuurt door de gebruiker goedgekeurde orders naar Interactive Brokers voor echte uitvoering. Het systeem is geen onderzoekstool en geen paper-only zandbak — het plaatst echte orders op echte accounts wanneer de gebruiker ze goedkeurt (doctrine §1).

## Account-modus: paper en real-money zijn gelijkwaardig
- De software werkt tegen één IBKR-account tegelijk. Of dat een paper-account of een real-money-account is, wordt door de gebruiker in IBKR bepaald.
- Beide modi delen dezelfde codepaden, berekeningen, suggestielogica, orderflow en audittrail (doctrine §3).
- Paper-modus dient uitsluitend om correct gedrag te verifiëren voordat het systeem op een real-money-account wordt aangesloten.
- Het dashboard toont permanent een onmiskenbare badge met de actieve modus (PAPER = geel, REAL MONEY = rood; doctrine §3.1).

## Orderflow: twee grids, twee goedkeuringen
- Elke order doorloopt twee grids met elk een eigen goedkeuring: de **suggested orders grid** (systeemvoorstel → IBKR parked) en de **IBKR todo grid** (parked → markt). Zie doctrine §4.
- Het systeem plaatst nooit een order zonder expliciete user-goedkeuring.

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

### Vereisten

- **Python 3.12** — backend (API + worker) en alle Python-packages targeten 3.12. Eerdere versies (3.10, 3.11) missen syntax-features die de codebase gebruikt.
- **Node 20+** — frontend (Next.js 14).
- **PostgreSQL 16** — gestructureerde opslag. Een Docker Compose-versie zit klaar in `infra/docker/docker-compose.yml`.
- **IBKR TWS of Gateway** (optioneel) — paper- of live-account. Vereist alleen wanneer je echte broker-sync of orderflow wilt testen; de stack start ook zonder.
- **EODHD API-key** (optioneel) — voor market-data + fundamentals. Zonder key valt market-data-leg terug op de stub.
- **Anthropic API-key** (optioneel) — voor Claude AI-uitleg + explainer batches. Zonder key blijft de stub-provider actief.

### Stap 0: environment-bestand

Kopieer het voorbeeld en pas de waarden aan voor je lokale install. Het bestand is bewust niet in git opgenomen.

```bash
cp infra/docker/.env.example infra/docker/.env
# Bewerk infra/docker/.env: POSTGRES_PASSWORD, STORAGE_DATABASE_URL,
# EODHD_API_KEY, CLAUDE_AI_API_KEY, IBKR_SYNC_HOST/PORT, etc.
```

Voor lokaal draaien zonder Docker exporteer je dezelfde variabelen in je shell of plaats je een `.env` naast `apps/api/` en `apps/worker/`.

### Stap 1: PostgreSQL via Docker

```bash
cd infra/docker
docker compose up -d postgres
```

Dit start alleen Postgres (poort 5432). Wacht tot `docker compose ps` rapporteert dat de healthcheck slaagt.

### Stap 2: Migraties uitvoeren

```bash
cd packages/storage
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
alembic upgrade head
```

Dit zet alle tabellen (runtime_config, ibkr_*, asset_*, scheduler_*, prediction_diary_*) op en zet `alembic_version` op de meest recente revisie.

### Stap 3: API-backend

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
uvicorn portfolio_outlook_api.main:app --reload --app-dir src --port 8000
```

De API draait nu op `http://127.0.0.1:8000`. Health-check: `curl http://127.0.0.1:8000/health` moet `{"status":"ok","service":"api"}` retourneren.

### Stap 4: Worker

```bash
cd apps/worker
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
python -m portfolio_outlook_worker.main
```

De worker start de APScheduler met de geconfigureerde cron-fires (morning chain 06:30, market-close digests, optionele order-sweeps). Hij schrijft elke 60s een heartbeat naar `scheduler_state`.

### Stap 5: Frontend

```bash
cd apps/web
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Dashboard staat klaar op `http://127.0.0.1:3000`. De `NEXT_PUBLIC_API_BASE_URL` env-var laat de frontend weten waar de API draait — in dev wijst die naar je lokale uvicorn, in productie naar de geïnstalleerde API-host.

### Stap 6 (aanbevolen): cold-start smoke test

Verifieer in één commando of de hele stack gezond is opgekomen:

```bash
python scripts/smoke_test.py --api-url http://127.0.0.1:8000
```

Exit-code `0` = alles groen en klaar voor paper-testing. `1` = warnings (bv. IBKR niet geconfigureerd). `2` = kritieke fout (DB onbereikbaar, migraties achter, blokkerende systeemmelding). Zie `docs/deployment.md` voor de volledige uitleg.

### Alles tegelijk via Docker Compose

```bash
cd infra/docker
docker compose up --build
```

Dit start Postgres + API + worker + web in één commando. Migraties draaien automatisch tijdens de API-startup.

### Settings achteraf wijzigen

Veel knoppen — IBKR-host, Claude-key, SMTP, AI-features, market-event toggles — zijn niet alleen env-vars maar ook persistent in `runtime_config` en bewerkbaar via de UI op `/instellingen`. Een save daar overschrijft de env-default; verwijderen valt terug op de env-waarde.


## Product-governance documentatie
- Version 1 scope register: `docs/product/version-1-scope-register.md`

## Eenvoudige Nederlandse UI-principe
Alle hoofdschermen, labels, waarschuwingen en acties moeten begrijpelijk zijn voor niet-experts. Elke veldwaarde krijgt eenvoudige Nederlandse helptekst/tooltip.

## Historische projectgeschiedenis (vóór doctrine 2026-05-26)

> De onderstaande paragrafen documenteren eerdere project-iteraties, waaronder een paper-only foundation-fase. Deze beschrijven historische beslissingen en code-toestanden die door de huidige doctrine (`docs/intent/_trading-system-doctrine.md`, vastgelegd 2026-05-26) zijn vervangen. Inhoudelijke regels in dit historische gedeelte zijn niet meer bindend — raadpleeg de doctrine voor de actuele werking.

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


## Project continuation / handover
- [project-handover.md](docs/product/project-handover.md)
- [current-state.md](docs/product/current-state.md)
- [locked-decisions.md](docs/product/locked-decisions.md)
- [version-1-backlog.md](docs/product/version-1-backlog.md)
- [next-task.md](docs/product/next-task.md)
- [task-history.md](docs/product/task-history.md)
- [new-chat-startup-prompt.md](docs/product/new-chat-startup-prompt.md)
