# GAPS.md — Complete software audit

**Datum**: 2026-06-14
**Doel**: Eerlijke, exhaustieve inventaris van alles wat nog niet werkt of niet doctrine-compliant is.
**Methode**: 8 parallelle Explore-agents (storage, IBKR/reconciliation, web UI, API wiring, worker scheduler, settings/env, test suite, dead code) + foreground smoke-test. Elke bevinding heeft file:line evidence.
**Doctrine bron**: `/home/user/ai-trading-agent/CLAUDE.md` versie V1.2 §AO

---

## Health rating per CLAUDE.md sectie

| § | Onderwerp | Status | Opmerking |
|---|---|---|---|
| §1 | Operator context | ✅ N/A | Geen code-impact |
| §2 | Operator beslist altijd | ✅ VOLLEDIG | Submitter vereist `user_approved`; take-profit pair null'd vóór submit; SELL alleen advies |
| §3 | Position sizing (confidence-tier) | ✅ VOLLEDIG | 50/30/15/skip exact in `profit_harvest.py:124-222`; €5k min hardcoded; 50% cap via `max_position_eur` setting |
| §4 | Universum (US+Euronext, stocks only) | ⚠️ PARTIAL | Backend OK; **ETF/Bond/per-exchange toggles ontbreken in UI** |
| §5 | Watchlist hybride (autoscan + favorieten + uitsluitingen) | ❌ INCOMPLETE | Universe scan default = 45 namen (doctrine zegt ~3500); 3e "Hybride" tab ontbreekt; favorieten-widget niet duidelijk op dashboard |
| §6 | Profit-harvest doctrine (+4%, soft horizon, combo-trigger) | ✅ CODE / 🔥 PRODUCTIE | Code-niveau volledig; **SELL-sweep wordt nooit automatisch getriggerd** (geen worker cron); **geen React-component rendert SELL-kaartjes** |
| §7 | Confidence + macro INFO-only | ✅ VOLLEDIG | <70%=skip; macro/sector evalueren maar blokkeren niet |
| §8 | Workflow drie stages | ⚠️ PARTIAL | /ibkr-acties tabs werken; **dashboard mist Stage-2 + Stage-3 widgets** |
| §9 | Per-kandidaat beslissingsdossier | ❌ INCOMPLETE | **Decision Package mist 5+ verplichte secties**: Risico, Order, Portfolio-impact, Earnings, Fundamentals, Dividenden, AI-uitleg, ISIN, bedrijfsnaam |
| §10 | Notificaties (geen email/sms) | ✅ VOLLEDIG | Email-config UI aanwezig maar geen scheduler triggers — past binnen doctrine |
| §11 | Pauze (SELL blijft draaien) | ✅ CODE / 🔥 PRODUCTIE | Code correct (`sell_signal_sweep.py:431` bypasst pauze); **maar sweep wordt nooit geactiveerd door worker** |
| §12 | /belasting pagina | ✅ VOLLEDIG | Alle 8 secties + PDF + CSV werken |
| §13 | /rapporten + auto-PDF archief | ⚠️ PARTIAL | Live pagina + handmatige PDF werken; **auto-PDF op 1e v.d. maand: geen scheduler job** |
| §14 | Settings UI /instellingen | ⚠️ PARTIAL | Basis-secties aanwezig; **ETF/Bond toggles ontbreken**; Watchlist 2-tab i.p.v. 3 |
| §15 | Doctrine-locks (paper, AI, TOB, secrets) | ✅ VOLLEDIG | Alle 6 enforced |
| §16 | Implementation roadmap | — | Statisch document |

**Eindscore**: 8 van 14 actieve secties volledig ✅, 6 hebben gaps.

---

## P0 — KRITIEKE GAPS (operator merkt dit direct, doctrine geschonden)

### P0-1: SELL-loop sweep wordt nooit automatisch getriggerd 🔥

- **Doctrine**: CLAUDE.md §6.3 + §11 — "SELL-monitoring blijft draaien"
- **Evidence**:
  - `apps/worker/src/portfolio_outlook_worker/scheduler.py:544-579` heeft alleen `submission_sweep` + `cancel_sweep`; geen `sell_signal_sweep` job geregistreerd
  - `sell_signal_sweep.run_sell_signal_sweep()` werkt perfect maar wordt alleen door `POST /sell-signals/sweep` aangeroepen (handmatig)
  - `sell_signal_sweep.py:431` bypasst pauze correct — maar de bypass is moot als de sweep nooit draait
- **Impact**: Operator mist élke +4% intraday hit. CLAUDE.md §11 "SELL blijft draaien" is een leugen.
- **Fix**: Voeg cron job toe in `_register_api_triggers()` (worker scheduler.py:425):
  ```python
  self._scheduler.add_job(
      lambda: trigger_sell_signal_sweep(api_base_url),
      "cron", minute="*/10", hour="7-21", day_of_week="mon-fri",
      timezone="Europe/Brussels", id="sell_signal_sweep_trigger",
      max_instances=1, coalesce=True,
  )
  ```
  + nieuwe helper `trigger_sell_signal_sweep` in `api_trigger.py`
- **Effort**: S (15 regels code + 1 test)

### P0-2: Geen React-component rendert SELL-kaartjes 🔥

- **Doctrine**: CLAUDE.md §6.3 — "SELL-suggestie kaartje op dashboard"
- **Evidence**:
  - `GET /sell-signals` werkt en geeft kaartjes terug
  - **Geen enkele `.tsx` file** in `apps/web/components/` consumeert de endpoint
  - `apiClient.ts` heeft GEEN `getSellSignals()` / `dismissSellSignal()` / `triggerSellSweep()` functies
  - Dashboard `apps/web/app/page.tsx` toont geen SELL-widget
- **Impact**: Zelfs als de sweep zou draaien (P0-1), de operator ziet de kaartjes niet.
- **Fix**: 
  1. `apps/web/lib/apiClient.ts`: 3 functies `getSellSignals()`, `dismissSellSignal(cardId, reason)`, `triggerSellSweep()`
  2. Nieuwe component `apps/web/components/SellSignalCards.tsx` met kaartjes (headline, current %, target, prob_above, EUR proceeds, "Verkopen nu" / "Houden" / "Verwijder uit lijst" knoppen)
  3. Integreer in dashboard tussen `ProfitHarvestCycleWidget` en `TodayActionsPanel`
- **Effort**: M (~150 regels + tests)

### P0-3: IBKR reconciliation sweep niet gewired 🔥

- **Doctrine**: T-035 reconciliation workflow + §2 audit trail
- **Evidence**:
  - `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/reconciler.py` heeft volledige `.tick()` methode
  - Geen scheduler job belt deze ooit
- **Impact**: Filled orders worden nooit gereconcilieerd; `action_draft.status` blijft op `submitted` zelfs na fill; `unmatched_executions` queue groeit; operator heeft geen IBKR↔DB consistency check.
- **Fix**: Cron `*/15 7-21 * * mon-fri` + cron `0 */1 * * mon-fri` in worker scheduler
- **Effort**: S-M (~30 regels)

### P0-4: Auto-PDF maandrapport ontbreekt 🔥

- **Doctrine**: CLAUDE.md §13 — "elke 1e van de maand wordt een PDF gegenereerd en opgeslagen in /rapporten/archief"
- **Evidence**:
  - `apps/api/src/portfolio_outlook_api/rapporten_routes.py:9-10` zegt expliciet "Auto-PDF generatie buiten scope"
  - `monthly_report_archive` tabel bestaat
  - Handmatige `POST /rapporten/archief/generate` werkt
  - Geen worker cron job
- **Impact**: Geen historisch archief; operator moet manueel elke maand triggeren.
- **Fix**: Cron `15 0 1 * *` Europe/Brussels in worker scheduler
- **Effort**: S (~15 regels)

### P0-5: Decision Package mist 5+ verplichte velden ❌

- **Doctrine**: CLAUDE.md §9 — volledige tabel van 11 categorieën
- **Evidence**: `apps/web/components/DecisionPackageDetail.tsx` rendert wel:
  - ✅ Identiteit (gedeeltelijk — sector/ISIN/bedrijfsnaam ontbreken)
  - ✅ Prijs
  - ✅ Forecast (p10/p50/p90)
  - ✅ Conviction (confidence badge)
  - ❌ **Risico (blockers near-miss)** — niet gerenderd
  - ❌ **Order (qty, limit, EUR totaal, TOB-kost)** — niet gerenderd in Decision Package detail
  - ❌ **Portfolio-impact (cash voor/na, sector blootstelling)** — ontbreekt
  - ❌ **Earnings (next earnings-datum)** — ontbreekt
  - ❌ **Fundamentals (sector, market-cap, P/E, momentum 6m/12m)** — ontbreekt
  - ❌ **Dividenden (verwacht tijdens hold + EUR netto na bronbelasting)** — ontbreekt
  - ❌ **AI uitleg (Claude NL paraphrase)** — ontbreekt in detail page
  - Backend `decision_package_export.py` response heeft ook NIET deze velden
- **Impact**: Operator kan geen geïnformeerde beslissing maken. Doctrine §9 is voor de helft niet gerendered.
- **Fix**: Twee PRs nodig:
  1. **Backend**: uitbreiden van `decision_package_export.py` response met fundamentals, earnings, dividenden, portfolio-impact, ISIN/bedrijfsnaam, order-sizing voorstel (`asset_fundamentals_snapshots`, `earnings_events`, `dividend_events`, en order-sizing via `conviction_weighted_position_size_eur`)
  2. **Frontend**: uitbreiden van `DecisionPackageDetail.tsx` met 7 nieuwe secties + types in `api-types.ts`
- **Effort**: L (Backend ~200 LOC, Frontend ~300 LOC, multi-day)

---

## P1 — HIGH-PRIORITY (doctrine-completeness)

### P1-1: Dashboard mist Stage-2 + Stage-3 workflow-widgets

- **Doctrine**: CLAUDE.md §8 — drie stage-blokken op dashboard
- **Evidence**: `apps/web/app/page.tsx` heeft alleen `TodayActionsPanel` (Stage 1) + `PendingApprovalsPanel` (semi Stage 2). Geen "Te verzenden naar IBKR" telling, geen "Verzonden naar IBKR" lijst.
- **Fix**: 2 nieuwe dashboard-widgets `Stage2BulkSubmitWidget`, `Stage3IbkrStatusWidget`
- **Effort**: M

### P1-2: 3e "Hybride" tab in Watchlist ontbreekt

- **Doctrine**: CLAUDE.md §5 + §14 — Favorieten / Uitsluitingen / Hybride
- **Evidence**: `WatchlistPreferencesSettings.tsx:424-437` toont 2 tabs
- **Fix**: 3e tab + hybride-mode-instellingen
- **Effort**: M

### P1-3: Favorieten-widget op dashboard met live confidence

- **Doctrine**: CLAUDE.md §5 — favorieten zichtbaar ook als ze door gates skippen
- **Evidence**: `FavorietenWidget.tsx` bestaat, integratie onduidelijk; geen "ook als gates falen" pad
- **Fix**: Widget integreren + endpoint die favorieten + their gate-uitkomsten teruggeeft
- **Effort**: M

### P1-4: Universe scan default = 45 namen (doctrine zegt ~3500)

- **Doctrine**: CLAUDE.md §5 — autonome scan ~3500 namen
- **Evidence**: `universe_registry.py:49` `DEFAULT_UNIVERSE_SET=STARTER_50`
- **Fix**: Default uitbreiden naar `EU600` of `SP500_PLUS_EU150` (~750 namen) + EODHD quota check
- **Effort**: S (config) + L (quota/perf testing)

### P1-5: Forecast-universe = positions-only

- **Doctrine**: CLAUDE.md §5 + §9 — favorieten moeten forecast hebben voor live confidence
- **Evidence**: `status_routes.py:1061` `positions = list(ibkr_repo.list_ibkr_position_snapshots(...))`. Favorieten + universe scan symbolen krijgen niets.
- **Fix**: `sync_forecasts(...)` uitbreiden met `extra_symbols` parameter; samenvoegen `positions + favorites + scan_results`
- **Effort**: M

### P1-6: ETF/Bond toggles ontbreken in /instellingen UI

- **Doctrine**: CLAUDE.md §4 + §14 — operator kiest "ETFs toelaten" / "Obligaties toelaten" default off
- **Evidence**: Backend `blocked_asset_types` werkt; checkboxes niet in `apps/web/app/instellingen/page.tsx`
- **Fix**: Twee checkboxes + binding aan `allow_accumulating_etfs` / `allow_bonds` settings
- **Effort**: S

### P1-7: Per-exchange enable toggles ontbreken

- **Doctrine**: CLAUDE.md §4 — per-beurs aan/uit-vinkje
- **Evidence**: Alleen globale `universe_set` toggle bestaat; geen per-exchange granular control
- **Fix**: Nieuwe settings `exchange_enabled_{NYSE, NASDAQ, EURONEXT_BR, EURONEXT_PA, EURONEXT_AS}` + UI + universe-scan filter
- **Effort**: M

### P1-8: /runbook web-pagina ontbreekt

- **Doctrine**: PR #635 / CLAUDE.md §16 — operator-checklist
- **Evidence**: `GET /runbook` werkt; `apps/web/app/runbook/` directory bestaat NIET
- **Fix**: Nieuwe pagina `apps/web/app/runbook/page.tsx` die GET /runbook consumeert
- **Effort**: S

### P1-9: Hardcoded magic numbers niet configureerbaar

- **Doctrine**: CLAUDE.md §6.2 (6m hold), §6.1 (4% target), earnings-block-window
- **Evidence**: 
  - `earnings_calendar_gate.py:57` hardcoded 5 trading days
  - `hold_position_review.py:46` hardcoded `DEFAULT_HORIZON_REVIEW_START_DAYS = 180`
  - `hold_position_review.py:47` hardcoded `DEFAULT_LOSS_FLOOR_PCT = Decimal("-5")`
- **Fix**: Verhuizen naar `runtime_config` + UI editable
- **Effort**: M

### P1-10: Data-refresh cron jobs ontbreken (FX, dividends, fundamentals)

- **Doctrine**: §9 Decision Package vereist deze data; §6.1 EUR-equivalent vereist verse FX
- **Evidence**: Geen scheduler jobs voor FX (`fx_rates`), dividend calendar, fundamentals snapshots
- **Fix**: 3 cron jobs in worker scheduler:
  - FX: `0 8,17 * * mon-fri`
  - Dividends: `0 9 * * mon-fri`
  - Fundamentals: `30 8 * * mon-fri`
- **Effort**: M (3 jobs + handlers)

---

## P2 — MEDIUM-PRIORITY (productie-robustheid + UX-polish)

### P2-1: IBKR connection heeft geen heartbeat / auto-reconnect

- **Evidence**: `ibkr_gateway.py:375` `is_connected()` peilt alleen op-aanvraag, geen achtergrond probe
- **Fix**: Heartbeat-task + reconnect-on-drop met exponential backoff
- **Effort**: M

### P2-2: Multi-account niet ondersteund

- **Evidence**: `submission_sweep.__init__()` accepteert één `ibkr_account_id: str`
- **Fix**: Per-account sweep + reconciler instantiation
- **Effort**: L (uit scope voor V1?)

### P2-3: Cold-start UX onduidelijk

- **Evidence**: Verse install → leeg dashboard, geen "wat moet ik nu doen" guidance
- **Fix**: Onboarding-banner + checklist op dashboard wanneer er geen positions/forecasts zijn
- **Effort**: M

### P2-4: Reconciler Pass C timeout = 24u (te lang)

- **Evidence**: Stale `submitted`/`accepted` drafts pas na 24u in manual_review queue
- **Fix**: Configureerbaar (default 4u)
- **Effort**: S

### P2-5: Storage layer — server_default inconsistentie

- **Evidence**: 39 `safe_for_*` kolommen gebruiken `server_default="0"` (string), 11 gebruiken `sa_false()` (Boolean)
- **Risk**: Cross-DB type coercion verschil — werkt op SQLite, kan falen op MySQL/Postgres edge cases
- **Fix**: Normaliseer naar `sa_false()` via één migratie
- **Effort**: M (1 migratie + test bumps)

### P2-6: Index gaps in storage

- **Evidence**: Geen indexes op `status` (12 tabellen), `created_at` (20+ tabellen), `asset_symbol`
- **Risk**: Dashboard queries traag bij >10k rijen
- **Fix**: 1 migratie met ~15 indexen
- **Effort**: S

### P2-7: Email-trigger jobs ontbreken (passend binnen doctrine)

- **Evidence**: `notification_routes.py:14-15` zegt expliciet "actual digest...wired in follow-up PR"
- **Doctrine §10**: "Geen notificaties" — dus dit is GEEN gap, eerder bewust niet gewired
- **Aanbeveling**: Of UI verbergen, of doctrine-text bijwerken
- **Effort**: S

### P2-8: Geen contract-drift detection (openapi ↔ routes ↔ TS-types)

- **Evidence**: 1209 API tests, geen test die verifieert dat openapi.json overeenkomt met routes; geen test dat `api-types.ts` overeenkomt met `openapi.json`
- **Risk**: Routes wijzigen in code, types blijven oud → frontend stuk in productie
- **Fix**: CI-step die regen't en diff't
- **Effort**: S

### P2-9: Morning chain mocks-heavy tests

- **Evidence**: `test_action_draft_submission_endpoints.py` monkeypatcht 4 storage repos tegelijk — proeft niet dat drafts daadwerkelijk persisteren
- **Fix**: Echte SQLite-DB integratie voor minstens 1 happy-path test per leg
- **Effort**: M

### P2-10: Macro feed sync heeft geen test

- **Evidence**: `macro_feed_sync.py` bestaat maar geen test verifieert het error-pad (EODHD outage)
- **Fix**: Test fixture + provider-stub voor error-pad
- **Effort**: S

### P2-11: Geen "rapporten Events sectie"

- **Doctrine §13**: "Pauze-momenten, macro alerts, vermeden earnings, settings wijzigingen"
- **Evidence**: `/rapporten` pagina mist deze sectie
- **Fix**: Nieuwe widget + backend query
- **Effort**: M

### P2-12: 175 van 253 API-endpoints niet door frontend geconsumeerd

- **Evidence**: API wiring audit telt 78 wired, 175 unwired
- **Fix**: Per-endpoint beslissen: ofwel UI bouwen, ofwel endpoint deprecaten
- **Effort**: L (audit + cleanup per groep)

---

## P3 — CLEANUP / TECH-DEBT

### P3-1: Dead code (1438 LOC in 8 modules)

Te verwijderen:
- `apps/api/src/portfolio_outlook_api/take_profit_submission_adapter.py` (135 LOC) — V1.2 §M doctrine officieel verwijderd
- `apps/api/src/portfolio_outlook_api/ai_ts_provider.py` (256 LOC) — vervangen door TsModelProviderProtocol
- `apps/api/src/portfolio_outlook_api/ibkr_account_snapshot_persistence.py` (177 LOC)
- `apps/api/src/portfolio_outlook_api/system_event_recorder.py` (156 LOC)
- `apps/worker/src/portfolio_outlook_worker/starter_watchlist.py` (317 LOC)
- `apps/worker/src/portfolio_outlook_worker/market_data_step.py` (283 LOC)
- `apps/worker/src/portfolio_outlook_worker/storage_readiness.py` (101 LOC)
- `apps/worker/src/portfolio_outlook_worker/health.py` (13 LOC)

**Effort**: S (delete + verify tests don't break)

### P3-2: Dead apiClient functies (9 stuks)

- `getLatestDailyBriefing()`, `getForecastLatest()`, `getLatestForecasts()`, `getLatestSchedulerRun()`, `getRecentSchedulerRuns()`, `getApiHealth()`, `getCalibrationCoverage()`, `getPredictorPerformance()`, `getLatestSuggestions()` — geen page roept ze aan

### P3-3: Dead API endpoints (5 stuks)

- `GET /briefings/daily/compute` (deprecated)
- `GET /forecasts/compute` (duplicaat van POST)
- `GET /prediction-diary` (geen caller)
- `GET /v1/release-readiness` (geen UI caller — maar wel handig voor smoke-test)
- `GET /universe/registry` (geen caller)

### P3-4: Duplicate endpoints

- `GET /decision-package/latest` vs `GET /decision-packages/latest` (singular vs plural)
- `GET /forecast/latest` vs `GET /forecasts/latest`

### P3-5: Stray artifacts in working tree

- `apps/api/dummy.db` (0 bytes)
- `apps/api/missing` (0 bytes)
- Toevoegen aan `.gitignore` of verwijderen

---

## P4 — BUILD/DEPLOY GAPS (smoke-test bevindingen)

### P4-1: `apps/web/Dockerfile:24` verwijst naar non-existent `public/` dir

- **Impact**: `docker compose build web` faalt
- **Fix**: `mkdir -p apps/web/public && touch apps/web/public/.gitkeep`

### P4-2: `.env.example` problemen

- `STORAGE_DATABASE_URL` uitgecommentaard maar `STORAGE_ENABLED=true` actief
- `POSTGRES_PASSWORD` heeft geen default; compose-up errort
- `EODHD_API_KEY`, `CLAUDE_AI_API_KEY` als placeholder strings
- **Fix**: Validator in Settings die `enabled+url=None` weigert; README-stap voor `.env` copy

### P4-3: Worker entry symbol drift

- Code exposeert `start_worker`, externe checks verwachten `main`
- **Fix**: Alias `main = start_worker` toevoegen aan `worker/main.py`

### P4-4: `docker-compose.yml` gebruikt `env_file: .env.example`

- **Risk**: Secrets-leak (zou `.env` moeten zijn)
- **Fix**: `env_file: .env` + README-stap

### P4-5: Geen `pnpm-workspace.yaml` ondanks pnpm-verwachting

- Project gebruikt npm; pnpm filter-commands falen
- **Fix**: Documentatie + `package.json` `workspaces` toevoegen of pnpm-ondersteuning

### P4-6: `BACKUP_GPG_PASSPHRASE_FILE` referent zonder `secrets:` block

- **Impact**: backup-target faalt silently
- **Fix**: `secrets:` block in docker-compose

### P4-7: Next.js niet in `standalone` output mode

- **Impact**: Docker image 300MB bloat
- **Fix**: `next.config.ts` `output: "standalone"` + Dockerfile aanpassen

### P4-8: Settings drift: starlette/httpx-deprecation warning

- TestClient emit deprecation op elke API-call
- **Fix**: `httpx<0.28` pin of migratie naar `httpx2`

---

## Concreet actieplan — voorgestelde PR-volgorde

### Sprint 1 — Maak SELL-loop écht werkend (P0-1 + P0-2)
**Doel**: Operator kan +4% kaartjes daadwerkelijk zien.

| PR | Inhoud | Effort |
|---|---|---|
| **PR §BI** | Worker cron job voor sell_signal_sweep + `trigger_sell_signal_sweep` in api_trigger.py + test | S |
| **PR §BJ** | `apiClient.ts` 3 nieuwe functies + `SellSignalCards.tsx` component + dashboard integratie + vitest | M |

### Sprint 2 — Decision Package compleet (P0-5)
**Doel**: Operator krijgt volledig dossier per kandidaat.

| PR | Inhoud | Effort |
|---|---|---|
| **PR §BK** | Backend: uitbreiden `decision_package_export.py` response met fundamentals, earnings, dividenden, portfolio-impact, ISIN/bedrijfsnaam, order-sizing voorstel | L |
| **PR §BL** | Frontend: `DecisionPackageDetail.tsx` met 7 nieuwe secties + types in `api-types.ts` | L |

### Sprint 3 — IBKR-reconciliation + auto-PDF (P0-3 + P0-4)
**Doel**: Audit-trail compleet, maandrapporten archiveren.

| PR | Inhoud | Effort |
|---|---|---|
| **PR §BM** | Worker cron job voor reconciler.tick() (15min market hours + 1u off-hours) | M |
| **PR §BN** | Worker cron job voor monthly_report_archive auto-generate op 1e v.d. maand | S |

### Sprint 4 — Doctrine-completeness §4/§5/§8/§14 (P1-1 t/m P1-7)
**Doel**: UI komt overeen met doctrine.

| PR | Inhoud | Effort |
|---|---|---|
| **PR §BO** | Dashboard Stage-2 + Stage-3 widgets | M |
| **PR §BP** | 3e "Hybride" tab in Watchlist + favorieten-widget op dashboard met live confidence | M |
| **PR §BQ** | ETF/Bond toggles + per-exchange toggles in /instellingen | M |
| **PR §BR** | Forecast-universe uitbreiden met favorieten + scan-results | M |
| **PR §BS** | Universe scan default verhogen naar EU600 (met EODHD quota-check) | S |

### Sprint 5 — Data-refresh + hardcoded magic numbers (P1-9 + P1-10)

| PR | Inhoud | Effort |
|---|---|---|
| **PR §BT** | FX-rate cron + dividend-events cron + fundamentals cron | M |
| **PR §BU** | Hardcoded constants (5d earnings, 180d hold, -5% loss) → runtime_config + UI | M |

### Sprint 6 — /runbook UI + cleanup (P1-8 + P3)

| PR | Inhoud | Effort |
|---|---|---|
| **PR §BV** | `/runbook` web-pagina | S |
| **PR §BW** | Dead code verwijderen (1438 LOC in 8 modules) | S |
| **PR §BX** | Dead apiClient functies + dead API endpoints opruimen | S |

### Sprint 7 — Productie-robustheid (P2)

| PR | Inhoud | Effort |
|---|---|---|
| **PR §BY** | IBKR heartbeat + auto-reconnect | M |
| **PR §BZ** | Storage: server_default normalisatie + index migration | M |
| **PR §CA** | Cold-start onboarding-banner | M |
| **PR §CB** | Contract-drift CI step (openapi ↔ routes ↔ TS) | S |
| **PR §CC** | Echte SQLite-DB integratie tests voor mocks-heavy paths | M |

### Sprint 8 — Build/deploy fixes (P4)

| PR | Inhoud | Effort |
|---|---|---|
| **PR §CD** | `apps/web/public/.gitkeep` + Dockerfile fix + `.env.example` validatie | S |
| **PR §CE** | Worker `main` alias + `docker-compose` `env_file: .env` + secrets block | S |
| **PR §CF** | Next.js standalone output + dep-drift fixes | M |

---

## Totale schatting

| Sprint | PRs | Geschatte effort | Doctrine-impact |
|---|---|---|---|
| 1 | 2 | 1-2 dagen | SELL-loop werkt écht |
| 2 | 2 | 3-4 dagen | Decision Package volledig |
| 3 | 2 | 1 dag | Audit-trail + maand-archief |
| 4 | 5 | 4-5 dagen | §4/§5/§8 compleet |
| 5 | 2 | 2 dagen | Data-versheid |
| 6 | 3 | 1-2 dagen | Cleanup + /runbook UI |
| 7 | 5 | 4-5 dagen | Robustheid |
| 8 | 3 | 1 dag | Deploy-klaar |
| **Totaal** | **24 PRs** | **17-22 dagen** | **Doctrine 100% |**

---

## Wat WERKT (om eerlijk in beeld te houden)

- ✅ `paper_only_mode=True` hard enforced via prefix-check
- ✅ Operator-beslist principe overal afgedwongen
- ✅ TOB 0,70% round-trip correct
- ✅ Confidence-tier sizing 50/30/15/skip exact volgens doctrine
- ✅ +4% target in lokale munt
- ✅ 0-6m hold window + 6m+ combo-trigger (beide condities vereist)
- ✅ Macro + sector ECHT INFO-only (blokkeren nooit)
- ✅ <70% confidence = skip, geen auto-drempel-verlaging
- ✅ Earnings-gate werkt (5-day block window)
- ✅ Pauze pauzeert BUY-leg, SELL bypasst pauze in code
- ✅ Claude AI alleen paraphrase, nooit forecaster
- ✅ Secrets (SMTP, Claude key) nooit in GET responses
- ✅ /belasting volledig (8 secties + PDF + CSV)
- ✅ /rapporten live pagina volledig (6.5 van 7 secties)
- ✅ /instellingen basis-secties aanwezig
- ✅ Workflow-stages in /ibkr-acties (button+modal i.p.v. typing)
- ✅ V1.2 §M auto-take-profit-pair officieel verwijderd (null'd vóór submit)
- ✅ Alembic chain 0001..0078 integriteit
- ✅ App imports schoon end-to-end
- ✅ Web build succeed
- ✅ OpenAPI consistent (geen dup operationIds, geen orphan schemas)

---

**Conclusie**: De doctrine-kern is correct gecodeerd. De productie-wireup heeft 5 kritieke gaten (P0), de UI is voor 50% van doctrine §9 niet gerendered, en er ligt 1438 LOC dood code. Met 24 voorgestelde PRs (geschat 17-22 werkdagen) is de software 100% doctrine-compliant en productie-klaar.
