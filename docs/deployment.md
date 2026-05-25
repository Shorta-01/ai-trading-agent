# Deployment

## Startplatform
Eerste deploymentdoel: Raspberry Pi 5 + NVMe SSD + Docker Compose + bedraad netwerk + actieve koeling + externe backups.

## Migratiepad
Latere migratie naar mini PC/zwaardere server zonder code rewrite.

## Verplichte principes
- Docker Compose als standaard runtime.
- Portabiliteit naar linux/arm64 en linux/amd64.
- Gebruik van env-files en named volumes.
- Geen hardcoded lokale paden.
- Geen secrets in code.

## Backups en restore
Dagelijkse backups + periodieke restore-tests; een backup geldt pas als betrouwbaar na geslaagde restore-test.
\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).
\n## Scheduler and background job planning\nContracts define planning only: plan -> eligibility -> skip/block/run status -> audit trace. Suggestion jobs require gezonde services en verse data; geen job voert trades uit. Zware AI/research taken horen in queue of externe worker, niet als onbeperkte Raspberry Pi scan.

## Task 16 foundation update
Settings/secrets metadata and OpenAI usage-cost budget contracts are added as domain-only foundations without real API calls or secret storage.
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.


## Database deployment planning (Task 21)
- PostgreSQL deployment is planned via Docker Compose in a later implementation task.
- Raspberry Pi 5 deployments must use portable Linux ARM64 images where practical, while keeping Linux AMD64 compatibility.
- No hardcoded local filesystem paths are allowed for persistence services.
- Connection strings must come from environment variables or secret references, never hardcoded in code.
- Database backups must be encrypted.
- Trusted-backup status requires a successful restore test, not only a backup file.


## PostgreSQL development service foundation (Task 22)
- A local PostgreSQL development service is now available in Docker Compose.
- Production and Raspberry Pi deployments must use safe env vars or secret references (no committed passwords).
- Named volumes holding persistence data must be backed up.
- Backups must be encrypted.
- Backup trust requires restore tests before being marked reliable.
- Deployment remains portable across `linux/arm64` and `linux/amd64` where practical.
- No Raspberry Pi-specific application logic may be introduced.

## Task 23 deployment note
- Alembic skeleton bestaat nu in `packages/storage`, maar er zijn nog geen migraties.
- Productie-database-URL moet later uit veilige env/secret-referenties komen.
- `alembic.ini` bevat alleen een placeholder, geen echte wachtwoorden.
- Backup/restore-tests blijven verplicht vóór persistence als betrouwbaar geldt.

## V1 release readiness (Task 177 / Slice 22)

Het `GET /v1/release-readiness` endpoint (Slice 22) aggregeert alle
operationele vlaggen tot een Dutch scorecard met stabiele blocker-codes.
De morning chain en de readiness-check delen dezelfde set vlaggen, dus
zodra het endpoint `status="ready"` rapporteert kan de 06:30
morning chain end-to-end draaien tegen het gekoppelde IBKR-paper
account.

### Vereiste env-variabelen voor V1

Opslag (verplicht):
- `STORAGE_ENABLED=true`
- `STORAGE_DATABASE_URL=postgresql+psycopg://...`
- `STORAGE_WRITES_ENABLED=true`

EODHD (verplicht voor market-data + fundamentals):
- `EODHD_ENABLED=true`
- `EODHD_API_KEY=<sleutel>`

IBKR (verplicht voor paper-spiegeling):
- `IBKR_ENABLED=true`
- `IBKR_SYNC_ENABLED=true`
- `IBKR_SYNC_HOST` / `IBKR_SYNC_PORT` / `IBKR_SYNC_CLIENT_ID` voor de TWS-koppeling.

Scheduler (verplicht voor 06:30 morning chain):
- `SCHEDULER_ENABLED=true`
- `SCHEDULER_TIMEZONE=Europe/Brussels`
- `SCHEDULER_DAILY_BRIEFING_CRON="30 6 * * *"` (default).

Morning-chain legs (alle verplicht voor end-to-end V1):
- `MARKET_DATA_SYNC_ENABLED=true`
- `FORECAST_SYNC_ENABLED=true`
- `SUGGESTIONS_SYNC_ENABLED=true`
- `DECISION_PACKAGES_SYNC_ENABLED=true`
- `ACTION_DRAFTS_SYNC_ENABLED=true`
- `DAILY_BRIEFING_SYNC_ENABLED=true`

Audit-pad (verplicht voor V1 acceptatie):
- `RECONCILIATION_SYNC_ENABLED=true`
- `PREDICTION_DIARY_SYNC_ENABLED=true`

### Operator runbook (dagelijks)

1. **07:00** — Open Portefeuille. De morning chain (gefireerd om 06:30)
   heeft de dagbriefing al berekend. Lees de Dutch samenvatting.
2. **Per draft** — Bekijk het Decision Package, de research-evidence en
   de AI-uitleg. Approve manueel als alles correct is. Geen draft
   vertrekt zonder approval.
3. **Na approval** — De action draft wordt via `POST
   /action-drafts/{id}/submit-to-ibkr-paper` verzonden. De
   reconciliatie-sync werkt FILL/CANCELLED-events bij; de Prediction
   Diary registreert het resultaat per horizon.
4. **Bij CI-failure** — Bekijk `GET /scheduler/runs/latest` voor de
   audit-rij; `error_text` toont de falende leg + code. Re-run met
   `POST /scheduler/runs/morning-chain` zodra het probleem is opgelost.
5. **Voor productie** — Poll `GET /v1/release-readiness`; zolang
   `status != "ready"` ontbreekt minstens één vereiste vlag of
   integratie. De manual approval-gate blijft altijd actief; een groene
   scorecard autoriseert geen order.

### V1 scope-lock

Slice 22 sluit de V1 expansion queue af. Post-V1 widening-ideeën
(zoals de volledige ~5 000-ticker universe-scan, echte TimesFM /
Chronos / Lag-Llama clients, conditional orders, GTC/OPG TIF, multi-
account portfolios, een mobiele app) blijven gedocumenteerd in
`version-1-backlog.md` maar zijn expliciet **buiten V1-scope**.
