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

### Tooling

Two scripts implement the mandate (run from the repo root, or via `make`):

- **`infra/docker/scripts/backup-postgres.sh`** (`make backup`) — `pg_dump`
  of the compose Postgres → `gzip` → **AES256-encrypted with GPG** → a
  timestamped file in `BACKUP_DIR`, then prunes files older than
  `BACKUP_RETENTION_DAYS`. Encryption is mandatory: the script aborts if
  `BACKUP_GPG_PASSPHRASE_FILE` is unset/unreadable.
- **`infra/docker/scripts/restore-test.sh`** (`make restore-test`) — restores
  the latest (or a given) backup into a **throwaway Postgres container**,
  verifies `alembic_version` and the public-table count, then tears it down.
  It never touches the production database. A backup is only TRUSTED once
  this passes.

### Configuration (`infra/docker/.env`)

- `BACKUP_DIR` — off-Pi destination (mount an external disk / NFS share;
  keep it off the boot media).
- `BACKUP_RETENTION_DAYS` — prune window (default 14).
- `BACKUP_GPG_PASSPHRASE_FILE` — path to a `chmod 600`, never-committed file
  holding the symmetric passphrase.

### Schedule (host cron example)

```cron
# Daily encrypted backup at 02:00
0 2 * * *  cd /path/to/ai-trading-agent && make backup   >> /var/log/ai-trading-backup.log 2>&1
# Weekly restore-test (Sunday 03:00) — proves the backups are restorable
0 3 * * 0  cd /path/to/ai-trading-agent && make restore-test >> /var/log/ai-trading-restore-test.log 2>&1
```

> The dump is pulled through `docker compose exec postgres pg_dump`, so the
> pinned `postgres:16.4` server + client versions always match. Combine with
> a UPS so a power cut triggers a clean shutdown rather than mid-write
> corruption.
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

### Cold-start smoke test

Na een verse install (of na een grote upgrade) gebruik
`scripts/smoke_test.py` om in één commando te verifiëren dat de hele
stack functioneert. Het script bevraagt de live API op vijf bestaande
status-endpoints (`/health`, `/storage/status/online`,
`/scheduler/v127/status`, `/ibkr/sync/status`, `/system/events/active`)
en geeft per concern één Nederlandse verdict-regel.

```
python scripts/smoke_test.py --api-url http://127.0.0.1:8000
```

Exit-codes:

| Code | Betekenis |
|------|-----------|
| 0    | Alles groen — install klaar voor paper-testing. |
| 1    | Alleen warnings (bv. IBKR niet geconfigureerd, geen events). |
| 2    | Kritieke fout (DB niet verbonden, migraties achter, blokkerende systeemmelding). |

Optionele flags: `--skip-ibkr` (handig voor een eerste install zonder
IBKR), `--skip-events`, `--no-colour`. Het script eindigt met exit-code
2 zodra ook maar één kritieke check faalt, zodat het in CI / cron
gebruikt kan worden als gatekeeper.

### V1 scope-lock

Slice 22 sluit de V1 expansion queue af. Post-V1 widening-ideeën
(zoals de volledige ~5 000-ticker universe-scan, echte TimesFM /
Chronos / Lag-Llama clients, conditional orders, GTC/OPG TIF, multi-
account portfolios, een mobiele app) blijven gedocumenteerd in
`version-1-backlog.md` maar zijn expliciet **buiten V1-scope**.

## V1.1 release readiness (Task 189 / Slice 34)

Met V1.1 voegt het `GET /v1/release-readiness` endpoint vijf nieuwe
blocker-codes toe aan dezelfde Dutch scorecard, gericht op het §22
oppervlak (rebuild-knoppen, Anthropic Claude-budget, universe-set).
De morning chain, het V1.1 acceptatietest en de readiness-check delen
dezelfde set vlaggen — een groene scorecard betekent dat zowel de V1
basis als de V1.1 §22 herbouw klaar zit voor productie.

### Nieuwe blocker-codes

- `ensemble_weight_strategy_invalid` — `ENSEMBLE_WEIGHT_STRATEGY`
  moet `equal_weight` (V1-gedrag) of `auto` (inverse-Brier weging)
  zijn.
- `predictor_backtest_disabled` — zet `PREDICTOR_BACKTEST_ENABLED=true`
  zodat de morning chain backtest-rijen kan persisteren voor de
  leaderboard + auto-weights.
- `claude_ai_api_key_missing_when_real_client_enabled` — de real
  Anthropic-client (uitleg of TS-predictor) is aan maar
  `CLAUDE_AI_API_KEY` ontbreekt. Stel de sleutel in of zet de
  real-client toggle uit (de stub blijft werken).
- `claude_ai_budget_exceeded` — live check tegen het
  `claude_ai_budget_usage` audit-tabel. Geactiveerd zodra opslag
  bereikbaar is; de cap is `CLAUDE_AI_BUDGET_MONTHLY_EUR` (default
  €50). Wanneer de cap bereikt is vallen beide Anthropic-providers
  terug op de stub.
- `universe_set_unknown` — `UNIVERSE_SET` moet in de locked set
  `{SP500, EU600, ALL_5K}` zitten.

### Extra env-variabelen voor V1.1

V1.1 §22-rebuild knoppen (default-waarden zijn V1-gedrag):

- `ENSEMBLE_WEIGHT_STRATEGY=auto` (default `equal_weight`).
- `PREDICTOR_BACKTEST_ENABLED=true` (default `false`).
- `UNIVERSE_SET=SP500|EU600|ALL_5K` (default `SP500`).
- `UNIVERSE_SCAN_CACHE_TTL_HOURS=24` (Slice 31, per-set EODHD cache).

V1.1 §22.2 Anthropic Claude (vereist alleen wanneer de real-client
toggles aan staan):

- `CLAUDE_AI_BUDGET_MONTHLY_EUR=50` (default €50; gedeeld tussen
  uitleg + TS predictor).
- `CLAUDE_AI_API_KEY=<sleutel>` (env-only; geen committed default).
- `CLAUDE_AI_EXPLANATION_MODEL=claude-haiku-4-5-20251001` (default).
- `AI_EXPLANATION_REAL_CLIENT_ENABLED=true|false`.
- `AI_TS_PREDICTOR_REAL_CLIENT_ENABLED=true|false`.
- `AI_TS_PREDICTOR_DAILY_ONLY=true` (default — real TS-call alleen
  vanuit de scheduler).

V1.1 §22.3 TIF + conditional orders (Slice 32) — gedrag is altijd
actief; geen extra env-vars. De order_type/TIF sets zitten in de code
gelockt: `LOCKED_ORDER_TYPES ⊇ {CONDITIONAL}`, `LOCKED_TIF_SET =
{DAY, GTC, OPG, IOC}`.

### V1.1 acceptatietest

`apps/api/tests/test_v1_1_acceptance.py` drijft de morning chain met
elke per-leg vlag aan + V1.1 rebuild-knoppen aan
(`ensemble_weight_strategy=auto`, `predictor_backtest_enabled=true`,
`momentum_horizon_scaled_thresholds=true`,
`qvm_sector_neutral_zscore=true`,
`mean_reversion_hurst_asymmetric_target=true`,
`gbm_regime_shift_enabled=true`) en verifieert dat:

1. De morning chain alle zes legs naar `succeeded` loopt.
2. De readiness scorecard `status="ready"` met `blockers=[]`
   rapporteert.
3. De manual approval-gate intact blijft (`safe_for_orders=false`,
   `safe_for_action_drafts=false` op elk response).

### V1.1 scope-lock

Slice 34 sluit de V1.1 expansion queue (Slices 23-34) af. Post-V1.1
widening-ideeën (volledige ~5 000-ticker EODHD bulk-list, real
TimesFM/Chronos/Lag-Llama clients, ibapi `Order.conditions`
submission-extensie, Next.js UX-panels op de Slice 33 routes,
multi-account portfolios, mobiele app) blijven gedocumenteerd in
`version-1-1-backlog.md` maar zijn expliciet **buiten V1.1-scope**.
