- Task 158 completed: baseline forecast engine end-to-end via lognormal GBM (Slice 3 of the V1 critical path, V1.1 stage). `compute_baseline_forecast` math in `packages/portfolio`, new `market_data_bars` + `asset_forecasts` tables (migration 0027), `EodhdClient.fetch_eod_bars`, `forecast_sync` orchestrator, `POST /forecasts/compute` + `GET /forecasts/latest` routes, Portefeuille "Verwachte richting" badge. Disabled-by-default; no AI, no suggestions, no orders.
- Task 157 completed: real market-data + FX provider via EODHD (Slice 2 of the V1 critical path). `EodhdClient` + `sync_market_data_and_fx` orchestrator + `build_market_data_provider` factory + `POST /market-data/sync` route. Disabled-by-default; no orders/suggestions/action drafts/broker execution added.
- Task 156 completed: real IBKR paper read-only sync runtime (Slice 1 of the V1 critical path). `IbapiReadOnlySyncClient` + `build_real_sync_adapter` factory + route wiring with context-managed `close()`. Disabled-by-default; no orders/suggestions/market-data/FX runtime added.
- Task 152-R6 completed: repair-only merged-red CI fix after Task 152-R5 for the `api` job `pytest` failures; fake-client execution helpers now enable the full Task 152 prerequisite gate set in tests, including dummy `ibkr_sync_host`, `ibkr_sync_port`, and `ibkr_sync_client_id` values alongside `ibkr_tws_readonly_real_client_enabled=True`. Missing host/port/client-id blockers remain tested for default/real configuration gaps, default-blocked tests still verify disabled-by-default safety-gated behavior, no-secret checks remain strict (no raw config/account payload leaks), and no production runtime behavior was widened (runtime default-disabled, readiness never connects, no sync/market-data/FX/suggestions/actions/orders/broker execution, no auto-connect/reconnect/persistent session manager, no schema/migrations, no `ib_insync`).
- Task 152-R5 completed: repair-only merged-red CI fix after Task 152-R4 for the `api` job `pytest` failures; fake-client execution helpers now enable the full Task 152 gate set including `ibkr_tws_readonly_real_client_enabled=True`, and remaining fake-client execution/error-path tests that still used `_settings(...)` were corrected to use `_fake_client_ready_settings(...)`. Default-blocked tests still prove disabled-by-default and safety-gated behavior. No production runtime widening: runtime remains disabled by default, readiness endpoint never connects, no account/portfolio sync, no positions/cash/open-orders/executions sync, no market-data runtime, no FX runtime, no suggestions/action drafts/orders/broker execution, no auto-connect/reconnect loop, no persistent session manager, no schema/migrations, no `ib_insync`, and no secret/raw broker payload exposure.
- Task 152-R4 — **Completed (repair-only):** repaired merged-red API `pytest` failures after Task 152-R3 by aligning stale fake-client manual status-check tests with Task 152 gate model (fake-client execution tests now enable all required prerequisite gates before expecting connect/check/disconnect), preserving default-blocked behavior checks, and tightening no-secret checks to reject exact raw configured values while allowing safe diagnostic code names (`missing_host`, `missing_port`, `missing_client_id`); no runtime behavior widening.
- Task 152-R2 — **Completed (repair-only):** API Ruff B009 failure after Task 152-R repaired in manual `ibapi` status client by replacing constant-attribute `getattr(...)` (`EClient`/`EWrapper`) with Ruff-compliant direct attribute access (narrow local Any-cast equivalent), while preserving typed protocol/factory isolation boundary and real manual status-check capability; runtime stays disabled-by-default with no behavior widening.
- Task 152-R — **Completed (repair-only):** API mypy failure after Task 152 repaired by typed protocol/factory boundary around untyped `ibapi` usage in manual status client; no behavior widening.
- Task 151: dependency-isolated `ibapi` façade toegevoegd (preflight-only, geen connectiviteit/wiring/runtimeuitbreiding).
- Task 150-R completed: merged-red repair na Task 150 voor API `pytest` failure in `test_repository_does_not_introduce_ib_insync`; preflightscan vernauwd naar projectmetadata + productie-runtime broncode i.p.v. alle repository-testbestanden, zodat bestaande safety-assertions met `ib_insync` in tests (zoals `packages/storage/tests/test_alembic_skeleton.py`) geen vals-positieve dependencyintroductie meer triggeren. `ibapi` blijft dependency/install-import preflight-only, geen productie-runtime import van `ibapi`, geen `ib_insync` dependency, geen runtime-connectiviteit/sockets by default, geen echte TWS/Gateway clientimplementatie, geen auto-connect/reconnect/persistente session manager, geen account/portfolio sync runtime, geen market-data/FX runtime, geen suggestions/action drafts/orders/broker execution, geen API/web-gedragswijziging en geen storage schema/migraties.
- Task 150 completed: selected `ibapi` dependency toegevoegd in `apps/api/pyproject.toml` voor dependency/install/import CI preflight; import smoke test toegevoegd in `apps/api/tests/test_ibkr_client_dependency_preflight.py` met no-socket guard op import. Geen productie-runtime import van `ibapi`, geen `ib_insync`, geen runtime-connectiviteit, geen echte TWS/Gateway clientimplementatie, geen auto-connect/reconnect/persistente session manager, geen account/portfolio sync runtime, geen market-data/FX runtime, geen suggestions/action drafts/orders/broker execution, geen API/web-gedragswijziging en geen storage schema/migraties.
- Task 149 completed: IBKR client dependency-selectie compatibiliteitspreflight (documentatie/preflight-only) toegevoegd; `ibapi` en `ib_insync` vergeleken zonder runtime-connectiviteit; geen runtime/API/web/storage-schemawijzigingen en geen dependency-introductie in projectmetadata. Aanbevolen vervolg: Task 150 dependency-only CI install/import preflight met voorkeur `ibapi`.
- [x] Task 148 — Completed: decision-gate document toegevoegd vóór echte TWS/Gateway client dependency-introductie (`ibkr-tws-client-dependency-decision-gate-task-148.md`) met vergelijking `ibapi`/`ib_insync`/dependency-free/defer en expliciete preflight-acceptatiecriteria. Documentatie/planning-only; geen runtime/API/web/storage schema/dependency/connectiviteit wijzigingen.
- Task 147-R completed: product-tracking drift na Task 147 gerepareerd; `next-task.md` wijst niet langer naar afgeronde Task 147 en is nu copy-paste klaar voor Task 148; `Huidige toestand` staat op `na Task 147-R`. Repair-only documentatie/product-tracking: geen runtime code gewijzigd, geen API-gedrag gewijzigd, geen web-gedrag gewijzigd, geen storage schema/migraties, geen echte TWS/Gateway runtime, geen echte low-level IBKR client, geen `ibapi`/`ib_insync`, geen socket/netwerkverbinding by default, geen auto-connect/reconnect/persistente session manager, geen account/portfolio sync runtime, geen market-data/FX runtime en geen suggesties/action drafts/orders/broker execution toegevoegd.
- Task 147 completed: operator-facing readiness diagnostics toegevoegd via GET /ibkr/session/manual-readonly-status-check/readiness; endpoint doet geen connectiepoging; runtime blijft default disabled; geen echte low-level client, geen ibapi/ib_insync, geen sockets/network by default, geen auto-connect/reconnect/persistente session manager, geen sync/market-data/FX runtime, geen suggesties/action drafts/orders/broker execution, geen schema/migraties.
- Task 146-R: **completed** — repair-only na merged-red Task 146/PR #342: CI-fout in `api` job (`mypy src`) hersteld door `_run_manual_tws_readonly_status_check_endpoint(...)` te voorzien van type-annotatie `runtime_settings: Settings`. Geen endpointgedrag gewijzigd; geen runtime-connectiviteit ingeschakeld; geen echte low-level IBKR-client; geen `ibapi`/`ib_insync`; geen socket/netwerk by default; geen auto-connect/reconnect/persistente session manager; geen account/portfolio sync runtime; geen market-data/FX runtime; geen suggesties, action drafts of orders toegevoegd.
- Task 146: manual read-only TWS/Gateway status-check endpoint shell toegevoegd; gebruikt Task 145 dependency-free runtime boundary, default/no-client runtime geblokkeerd, fake clients alleen test-only, runtime default uit, geen ibapi/ib_insync/sockets/auto-connect/reconnect/persistente sessie/sync/market-data/FX/suggesties/action drafts/orders/broker execution/migraties.
- Task 144 completed: expliciete preflight-checklist toegevoegd voor toekomstige echte TWS/Gateway read-only runtime-connection enablement, inclusief harde configuratie/account-mode/lifecycle/no-secret/failure-handling/test gates. Deze taak is documentatie/preflight-only: geen runtime connectivity enabled, geen echte low-level IBKR client, geen auto-connect/reconnect loop/persistente session manager, geen account/portfolio sync runtime, geen market-data/FX runtime, geen suggesties/action drafts/orders/broker execution en geen storage schema/migraties.
- Task 143 completed: read-only IBKR session-status diagnostics uitgebreid met expliciete adapter-readiness en blocked runtime reason-codes; default blijft veilige non-network adapter en orders/suggesties/actions blijven geblokkeerd.
- Task 142 completed: disabled-by-default TWS/Gateway adapter factory wired behind explicit setting with safe diagnostics; default remains non-network safe adapter and all order/suggestion/action booleans blocked.
## Task 141
- Completed: milestone-sized Milestone B adapter-boundary slice met disabled-by-default TWS/Gateway read-only session-status adapter skeleton op injected-client protocol boundary.
- Bevestigd: geen runtime connectivity by default, geen auto-connect/reconnect loop, geen persistente session manager, geen account/portfolio sync runtime, geen market-data of FX runtime, geen suggesties/action drafts/orders/broker execution, geen secrets/raw broker payload exposure en geen storage schema/migraties.

## Task 140-R
- Completed: repair-only fix na merged-red Task 140 voor API `mypy src` failure in reconciliation readiness (`IbkrSyncRunRecord` payload-validatie-attributen bestonden niet in storage contract).
- Durable sync records gebruiken nu conservatieve payload-validatie fallback (`not_available` / `Niet beschikbaar` / geen opgeslagen payloadvalidatie-details) zonder historische details te verzinnen.
- Geen storage schemawijzigingen of migraties; geen echte TWS/Gateway runtime; geen persistente session manager; geen market-data runtime; geen FX runtime; geen suggesties/action drafts/orders/broker execution toegevoegd.

## Task 140
- Completed: read-only reconciliation readiness endpoint toegevoegd (`GET /portfolio/valuation/reconciliation-readiness`) die bestaande waarderingblockers samenvat zonder waarden te verzinnen en met alle order/suggestie/action safetybooleans geblokkeerd. Geen TWS/Gateway runtime, geen session manager, geen schema/migraties, geen market-data/FX runtime, geen suggesties/action drafts/orders/execution.

- Task 138 is afgerond: adaptercontract-hardening + deterministische test-only fake fixtures + foutclassificatie-tests voor read-only IBKR sync voltooid zonder runtimeverbreding.
## Task 136 update
- Completed: durable IBKR sync status contract alignment with Task 135B payload-validation/safety fields.
- Durable historische runs zonder payload-validatie-opslag rapporteren conservatief `payload_validation_status: not_available` met Nederlandse helptekst; er worden geen historische validatiefouten verzonnen.
- Geen storage schema/migraties en geen runtime-uitbreiding (geen TWS/Gateway runtime, market-data runtime, suggesties, action drafts, orders of broker execution).

## Repair update — Task 135B-R
- Completed: repair-only fix for merged-red Task 135B API Ruff E501 failures.
- No runtime scope added; no storage schema/migration changes; no market-data runtime, suggestions, action drafts, orders, or broker execution added.

- [x] Task 134B-R2 — Completed: Task 134B-R2 repaired the remaining API pytest failures after merged Task 134B-R by preventing readiness recomputation in the final `run_sync(...)` response: readiness was first computed with the injected session-status adapter, then incorrectly recomputed by `read_status(settings)` without that adapter; `run_sync(...)` now returns status using the same precomputed readiness object. No real TWS/Gateway network runtime, no real IBKR account/portfolio sync runtime, no market-data runtime, no suggestions, no action drafts, no Decision Packages runtime, no orders, no broker execution, no financial calculations and no fake data were added.
## Next up
- Task 135B: volgende implementatiestap blijft geldig na Task 135A audit/reconciliatie; scope blijft hard beperkt tot het verharden van IBKR read-only sync adapter payloadvalidatie voor cash/positions/open orders/executions zonder echte TWS/Gateway runtime, zonder market-data runtime, zonder suggesties, zonder action drafts en zonder orders.

- [x] Task 135A — Completed: documentation-only audit/reconciliatie uitgevoerd om repository/producttracking opnieuw te verankeren op GitHub-truth na PR #326; geen runtimecode, API, web, storage, migraties of netwerkgedrag gewijzigd.

- [x] Task 134B-R — Completed: repair na merged Task 134B voor API pytest-failures door incomplete test settings op de session-status zijde van de readiness gate; `_base_settings(**kwargs)` in `apps/api/tests/test_ibkr_sync_endpoints.py` configureert nu sync + session-status defaults override-safe. Geen productieruntimewijziging buiten test/config repair; geen echte TWS/Gateway netwerkruntime, echte IBKR account/portfolio sync runtime, market-data runtime, suggesties, action drafts, Decision Packages runtime, orders, broker execution, financiële berekeningen of fake data toegevoegd.

- [x] Task 133B-R — Completed: product-tracking repair voor ontbrekende Task 133B scope-register notitie + checker-hardening voor latest-completed-task aanwezigheid in `current-state`, `task-history`, `version-1-backlog` en `version-1-scope-register`; geen runtimewijzigingen.

- [x] Task 133B — Completed: minimale IBKR read-only sync readiness/preflight status gate via pure statusbuilder + exposure op `GET /ibkr/sync/status`; geen real sync runtime of TWS/Gateway network runtime, geen account/portfolio sync runtime, geen market-data runtime, geen suggesties/action drafts/orders/broker execution, geen financiële berekeningen en geen fake data toegevoegd.

- [x] Task 132B — Completed: document-first selectie van de volgende veilige Milestone B IBKR read-only sync foundation batch vastgelegd in `docs/product/ibkr-read-only-sync-foundation-batch-selection-task-132b.md`; selectie wijst naar Task 133B; geen runtime/API/storage/migratie/netwerk/sync/market-data/suggesties/action drafts/orders/broker execution/financiële berekeningen/fake data toegevoegd.

- [x] Task 125V — Completed: Task 125U wording-catalogus toegepast op read-only valuation readiness UI labels/helpteksten; alleen UI copy/helptekst/fallback updates; geen API/storage/migratie/runtime fetch/berekeningen/suggesties/action drafts/orders/broker execution/fake waarden en geen browser-side money/P&L parsing.
- [x] Task 125K — Completed: pure Decimal-only conversion-total calculator module + unit tests op opgeslagen inputs; geen API wiring, geen endpointgedragwijziging, geen runtime FX/provider fetch, geen market-data runtime, geen suggesties/action drafts/orders en geen fake FX-rates/converted totals.
- [x] Task 125J — Completed: document-first valuation conversion-total preflight met veilige Decimal-only criteria en contract/status/teststrategie voor toekomstige totals op basis van opgeslagen inputs; geen runtime berekening/fetch/suggesties/orders en geen fake FX/totals.
- [x] Task 125F — Completed: read-only FX snapshot-contract inventaris + valuation readiness contractstatus voor ontbrekende FX-opslagcontracten; geen runtime fetch en geen fake FX/totals.
- Task 127: **completed** — documentation-only alignment voor account-mode-aware productrichting, action-draft/Prediction Diary/alerts/daily briefing decision locks. Geen runtimewijzigingen.
- Task 126 (documentation/research): afgerond — `docs/product/asset-suggestion-algorithm-roadmap.md` toegevoegd als beslis- en architectuurroadmap voor toekomstige suggestielaag; runtime blijft ongewijzigd.
- [x] Task 125C-B — Completed: wire IBKR read-only sync manual-trigger runtime to durable storage behind small persistence boundary with in-memory fallback; no orders/suggestions/fake data, no real IBKR network adapter or TWS/IB Gateway connection added.
- [x] Task 125C-A — Completed: small mapper + persistence façade scaffolding for durable IBKR sync storage bridge (API-side only); endpoint runtime behavior not replaced yet.
- [x] Task 125B — Completed in PR #258: IBKR sync storage repository dataclasses/records en SQL repository methods voor duurzame snapshot-tabellen toegevoegd (incl. public exports + storage tests); geen API/runtime wiring, geen orders, geen suggesties, geen fake data.

- Task 122: **completed** — IBKR TWS/Gateway technical preflight documentatie toegevoegd en read-only IBKR sessiestatuscontract uitgebreid (disabled-by-default, geen auto-connect, geen orders, safety booleans false).

- Task 120: **completed** — disabled-by-default IBKR paper marktdata-adapter skeleton en handmatige latest-snapshot fetch route toegevoegd (status-first, read-only, geen scheduler/background fetch, geen fake data, safety booleans false).

- Task 112: **completed** — read-only request-audit detail drilldown pages toegevoegd voor request logs, provider/sources en freshness-audits, inclusief cross-links tussen request logs en freshness-audits waar linked IDs bestaan, plus web API client detail-contract hardening. Scope bleef non-runtime: geen provider calls, geen market-data runtime, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical fetching, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen IBKR connectie/orders en geen fake data. Task 107 tracking-drift preventieregel gevolgd; CI-check uitgevoerd vóór implementatie.

- Task 111: **completed** — conservatieve read-only audit viewer/API visibility foundation toegevoegd voor request logs, provider/source metadata en freshness-audit records in web UI. Geen provider calls, geen market-data runtime, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical fetching, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen IBKR connectie/orders en geen fake data. Safety booleans blijven conservatief false/blocked.

- Task 130 is afgerond en uit backlog gehaald: IBKR read-only session-status boundary/API exposure (veilig, disabled-by-default, non-network default adapter).

## Task 110E update

- Task 110E voltooid: read-only/status API exposure toegevoegd voor `/audit/request-logs`, `/audit/provider-sources` en `/audit/freshness-audits` (incl. detail endpoints), met API tests en producttracking bijgewerkt; non-runtime grenzen en conservatieve safety booleans (`false`) behouden.

# Version 1 Backlog (operational source of truth)

Zie ook de einddoelarchitectuur in `docs/product/final-solution-vision.md`.

## A) Completed foundations

- [x] Task 137 — Completed: planning/documentation-only selectie van de volgende milestone-sized Milestone B implementatieslices vastgelegd in `docs/product/milestone-b-next-implementation-slices-task-137.md`; Task 138 geselecteerd als volgende implementatiestap; geen runtime/API/web/storage/migratie/netwerk/suggestie/order/broker-execution wijzigingen.
- [x] Task 131B-R — Completed: repair na merged Task 131B voor wrong-account-mode status regression in API pytest (`account_mode_status` was `unknown` i.p.v. `mismatch`); normalisatie hersteld zonder runtime-scope-uitbreiding (geen echte IBKR-netwerkadapter/auto-connect/sync/market-data runtime/suggesties/action drafts/Decision Packages/orders/broker execution/financiële berekeningen/fake data).
- [x] Task 129 — Completed: Milestone B IBKR read-only runtime slice selectie/documentatie afgerond (`milestone-b-ibkr-read-only-runtime-slice-selection-task-129.md`); Task 130 geselecteerd als volgende kleine implementatieslice; planning-only, geen runtime/API/storage/migratie/fetch/calc/suggestion/action-draft/order/broker/fake-data wijzigingen.
- [x] Task 128 — Completed: workflow accelerationlaag toegevoegd (nieuwe procesdocs, task template, milestone queue, red/green CI workflow en optionele lokale helper scripts); Task 125W micro-audit pad gedeferreerd/vervangen; geen runtime/API/storage/migratie/fetch/calc/suggestion/action-draft/order/broker/fake-data wijzigingen.
- [x] Task 128-R — Completed: product-tracking drift repair op `current-state.md` marker + kleine checker-hardening voor stale `Huidige toestand` detectie; Task 129 blijft volgende taak; geen runtime/API/web/storage/migratie/fetch/calc/suggestion/action-draft/order/broker/fake-data wijzigingen.

- [x] Task 125G — Completed: document-first/read-only FX snapshot storage contract preflight toegevoegd (`docs/product/fx-snapshot-storage-contract-preflight-task-125g.md`); geen migraties of runtime implementatie toegevoegd.

- Task 109 completed: documentatie/design-only preflight voor request logs + provider/source metadata + freshness-audit records (`docs/product/request-log-provider-freshness-contract-preflight-task-109.md`). Candidate veldcatalogi + status/reason-code voorstellen + traceability-linking vastgelegd. Geen storagetabellen/migrations/endpoints/schedulers/runtime-fetching/latest-price fetching/forecast runtime/AI runtime/suggesties/Decision Packages runtime/actiedrafts/orders/fake data toegevoegd; Task 107 tracking-drift preventieregel gevolgd.
- repository/API/worker/web/docker/CI skeleton
- settings/status foundations
- system events foundation
- IBKR contracts/placeholders
- research source archive storage/API/UI
- safe upload
- TXT/MD/CSV extraction
- deterministic classification
- prompt-injection scan status storage/API
- source credibility status storage/API
- source evidence item storage/API
- probabilistic asset outlook doctrine
- CI quality rules
- asset master identity foundation (Task 71 storage/API, referentie/status-only)
- source-to-asset linking foundation (Task 72 storage/API, audit/reference/status-only, blocked for suggestions)

## B) Still missing for Research Library

- PDF/DOCX/XLSX/PPTX extraction
- OCR (indien nodig)
- URL fetching + veilige snapshotting
- echte prompt-injection analysis engine
- echte source credibility scoring engine
- Evidence Ledger API/linking
- evidence review UI
- source conflict detection runtime
- source freshness/runtime validation
- asset detection from sources
- source-to-asset linking runtime/detection/matching beyond foundation (Task 72 foundation completed; audit/reference-only, blocked for suggestions)
- watchlist proposal flow met user confirmation
- multi-year report comparison runtime

## C) Still missing for core product

- asset master runtime verdieping (advanced identity validation/mapping)
- market data storage
- adjusted/unadjusted historical price data
- corporate actions
- FX rates + freshness
- market calendar runtime
- feature store
- forecast target definitions
- probabilistic baseline model
- backtesting/walk-forward validation
- probability calibration
- model registry/model risk controls
- scenario engine
- portfolio-level probability/risk
- suggestion engine runtime
- portfolio grid (read-only snapshot UI toegevoegd in Task 77; verdere runtime-verdieping pending)
- watchlist grid
- action badges + explanation panel
- IBKR read-only integration (positions/cash/open orders/executions snapshots foundation toegevoegd in Task 75/76; echte connectieruntime pending)
- account mode verification
- broker snapshots
- reconciliation
- toekomstige account-mode-aware IBKR Action Center
- user-approved broker submission na validation/dry-run/final confirmation (pas na alle gates)
- audit viewer
- AI event intelligence
- OpenAI usage/cost dashboard
- Belgian tax/compliance support
- deployment/backups/restore testing

## D) Future but not Version 1

- live trading
- automatische trading
- unapproved broker action
- unattended broker execution
- silent submit/modify/cancel
- automatic orders
- options
- futures
- leverage
- short selling
- crypto
- penny stocks
- CFDs
- complex derivatives
- high-frequency trading

- Task 68 completed: Evidence Ledger API/linking foundation voor research source evidence (audit-only, geen suggestion unlock).
- Task 69 completed: gate outcome + freshness policy foundation als storage/API basis (audit/status-only, geen suggestion unlock).
- Task 69B completed: repair op Task 69 met CI terug groen en zonder runtimegedrag te wijzigen.


- Task 70 completed: source conflict detection foundation (storage/API) als audit/status records; geen suggestion unlock.


## E) Post-Task 72/72B/72C sync status

- Task 72: source-to-asset linking **foundation exists** (storage/API, audit/reference-only).
- Task 72B: storage mypy row-to-record typing en API pytest 503 failures gerepareerd; geen runtimegedrag gewijzigd.
- Task 72C: resterende API pytest source-link create→list fake repository persistence failure gerepareerd; geen runtimegedrag gewijzigd.
- CI-status na Task 72C: **groen**.
- Source-to-asset links: **audit/reference/status-only**.
- Source-to-asset links: **blocked for suggestions**.
- Asset detection from sources: **runtime pending**.
- Watchlist proposal/user-confirm flow: **runtime pending**.
- Market data/freshness/runtime validation: **runtime pending**.
- Suggestion engine runtime: **runtime pending**.
- Probabilistic forecast runtime: **runtime pending**.
- IBKR runtime: **runtime pending**.


## F) Release 1 functional workflow capabilities (locked, not implemented yet)

Volgende capabilities zijn verplicht voor Release 1 volgens `docs/product/release-1-functional-workflow-blueprint.md` en zijn momenteel **niet geïmplementeerd**:

- IBKR sync engine (positions, cash, orders, executions/fills, timestamps)
- market data engine (freshness + recalculation inputs)
- Decision Package storage/API/UI
- Suggestions-grid (Actief / Verlopen / Historiek)
- IBKR Action Center (Te keuren / Actief bij IBKR / Historiek)
- actie-draft workflow (prefill, edit, approval, submit, lock, status-follow-up)
- safety checks + instellingen (draft en backend hard checks)
- usable-cash berekening voor buy-readiness
- AI-analytics modules + schema-valid, versioned signal outputs
- daily portfolio/watchlist briefing
- user upload → recalculation/revalidation triggers
- Release 1 end-to-end acceptance workflow

Belangrijk: dit zijn functionele werkitems voor toekomstige implementatietaken; deze PR voegt geen runtimecode toe.


## G) Task 74 update

- Moderne GUI shell + dashboard foundation is toegevoegd.
- Dashboard gebruikt veilige empty states: geen fake portfolio-/broker-/suggestiedata en geen fake chartwaarden.
- Navigatie-shell voor Release 1 workflow bestaat (Dashboard, Portefeuille, Volglijst, Suggesties, IBKR Acties, Onderzoek, Historiek, Instellingen).
- Geen IBKR runtime, market-data runtime, suggestion runtime, AI runtime of ordergedrag toegevoegd.

- [x] Task 75 — IBKR portfolio sync engine foundation (read-only status + portfolio snapshots + API basis).
- [x] Task 76 — IBKR executions/open-orders sync foundation (read-only snapshots + API; geen ordersubmission/-wijziging/-cancel, geen action drafts/suggesties/Decision Packages/AI/market-data/forecast runtime, geen fake broker/order/execution data).
- [x] Task 76B / PR #153 — API mypy repair op sync run count typing (`int`), CI terug groen, geen runtimewijziging.
- [x] Task 77 — Read-only Portefeuille-grid UI vanuit bestaande IBKR snapshot-endpoints (`/ibkr/sync/status`, `/ibkr/portfolio/positions`, `/ibkr/account/cash`, `/ibkr/orders/open`, `/ibkr/executions`), zonder ordergedrag/suggesties/AI/market-data/forecast of fake data.
- [x] Task 78 — Watchlist foundation + read-only Volglijst page (lokaal/manueel, gescheiden van IBKR-posities).
- [x] Task 78B — CI-repair na Task 78 (API ruff-formatting + storage stale migration/metadata expectations); geen runtimegedrag gewijzigd en geen nieuwe features toegevoegd.

- [x] Task 80 — Asset Master search/picker UI foundation (read-only/reference-only; voltooid).


## Task 81 lock — required work before market-data runtime (not implemented yet)

- IBKR contract search/validation foundation *(not implemented yet)*
- IBKR conid mapping for Asset Master *(not implemented yet)*
- Volglijst add flow converted to IBKR contract picker *(not implemented yet)*
- System-detected asset candidate resolution through IBKR contract search *(not implemented yet)*
- IBKR watchlist import foundation *(not implemented yet)*
- IBKR watchlist export foundation later *(not implemented yet)*
- Watchlist sync conflict handling *(not implemented yet)*
- Asset data-readiness status *(not implemented yet)*
- Historical data backfill queue *(not implemented yet)*
- Latest market snapshot scheduler *(not implemented yet)*
- Hot/warm/cold asset refresh tiers *(not implemented yet)*
- Fast alert layer foundation *(not implemented yet)*
- AI event analysis trigger foundation *(not implemented yet)*

- Task 82 completed: read-only IBKR contract search/validation foundation (identity/reference-only) toegevoegd; Volglijst add-flow conversie naar verplichte contractpicker blijft open voor Task 83.

- [x] Task 84 — IBKR watchlist import foundation (read-only adapter boundary, conid-normalisatie, import-candidates; geen write naar IBKR).
- [x] Task 84C — CI-repair na PR #163: API pytest test setup gecorrigeerd (`Settings.model_copy(update=...)` i.p.v. `dataclasses.replace()` en expliciete IBKR settings patch voor configured-path). Geen runtimewijzigingen, geen scope-uitbreiding; Task 85 pas na groene CI.


## Task 85 update

- Task 85 voltooid: conservatieve market-data storage/freshness foundation toegevoegd (schema + status-only API readiness endpoint).
- Geen market-data runtime toegevoegd, geen historical fetching, geen scheduler, geen AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag.
- Geen fake market prices of fake broker/recommendation data toegevoegd.
- Ongevalideerde of onopgeloste identiteiten blijven geblokkeerd voor market data en latere analyse/suggesties/actie-drafts.

- [x] Task 86 — Market data readiness persistence wiring (read-only snapshotmetadata, conid-gated readiness blijft actief).

- [x] Task 86B — API CI-repair na Task 86 (mypy typing boundary fix in market-data readiness detail endpoint; geen runtime features toegevoegd, geen market-data runtime/historical/scheduler/AI/suggesties/action drafts/IBKR-ordergedrag/fake data).

- [x] Task 87 — Conservatieve watchlist/readiness inspectieverbetering (read-only): duidelijkere Nederlandse blocked/missing-snapshot statusuitleg en auditvelden toegevoegd; geen market-data runtime/historical/scheduler/AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag/fake data.


- [x] Task 88 — Conservatieve readiness-contract consolidatie (API-only, read-only): typed readiness responsemodellen/helpers gecentraliseerd, regressietests uitgebreid; geen runtimegedrag toegevoegd.
- [x] Task 88B — CI-repair na Task 88: import-boundary/type-fix in readiness-contract module (protocol i.p.v. route-model import), zonder runtimewijzigingen of scope-uitbreiding.
- [x] Task 88G — Documenteer CI-platformblokkade na PR #171: 6 normale CI jobs + CI Diagnostic falen; diagnostische workflow faalt vóór logs/artifacts; geen geverifieerde application-code root cause.
- [x] Task 88L — CI unblock task afgerond (repository visibility change naar public; GitHub Actions execution/logging hersteld). CI run #358 groen met 6 geslaagde jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
- [x] Task 89 — conservatieve API-readiness contract hardening (read-only/API-contract/tests): extra response-contract regressietests + expliciete typed snapshot-detail coverage; geen runtime fetching/analyse/scheduler/AI/suggesties/Decision Packages/action drafts/orders/fake data.
- [x] Task 90 — conservatieve market-data readiness API cleanup (read-only/API-contract/tests): snapshot-latest endpoint naar expliciet typed responsecontract + regressietests voor not-configured/missing-snapshot/storage-failure en metadata-only semantiek; geen runtime fetching/analyse/scheduler/AI/suggesties/Decision Packages/action drafts/orders/fake data.
- [x] Task 91 — conservatieve market-data readiness status enum-normalisatie + regressiehardening (read-only/API-contract/tests/docs): expliciete typed list/detail readiness-statussen en stabiele NL help/status regressietests; latest-snapshot varianten behouden en getest; geen runtime fetching/historical/scheduler/AI/suggesties/Decision Packages/action drafts/orders/fake data.
- [x] Task 92 — conservatieve market-data readiness explainability + boundary-consistency hardening (read-only/API-contract/tests/docs): stabiele NL explainability/helptekst, expliciete `analysis_ready=false`/`suggestions_allowed=false`/`action_drafts_allowed=false`, deterministische blocked/ready/snapshot regressies incl. detail/latest-snapshot non-implication coverage; geen runtime fetching/historical/scheduler/AI/suggesties/Decision Packages/action drafts/orders/fake data.


- [x] Task 88H — tijdelijke CI-diagnostische workflow verwijderd (`.github/workflows/ci-diagnostic.yml`) na bevestiging dat failure buiten normale project test/lint/build-output ligt; CI-blokkade blijft gedocumenteerd, normale CI blijft rood en Task 89 blijft geblokkeerd tot CI groen is.


## Accepted architecture-audit todo items (Task 88I)

- **CI-blocker opgelost in Task 88L**: GitHub Actions logs/executie zijn hersteld na visibility change naar public; normale regel blijft: featurewerk alleen bij groene CI.
- **Asset identity hardening vóór serieuze runtime**: roadmap voegt expliciete `AssetMaster` (entiteit/bedrijf) + `AssetListing` (verhandelbare listing/instrument) splitsing toe. IBKR `conid` hoort op listing-niveau; model moet conid-history, primary/routing exchange, listing/settlement currency, ADR-underlying relaties, corporate-action identity changes en unresolved identity blockers ondersteunen.
- **Geen serieuze analyse op losse tickertekst**: geen market data, suggesties of action-drafts op ambiguë/onopgeloste identiteit.
- **IBKR Gateway skeleton (read-only/safe boundary) gepland**: centrale sessiestatus, auth/account-mode status, tickle/keepalive, request logging, pacing awareness, foutafhandeling, account-mode visibility/verification enforcement en latere order-serialisatiegrens.
- **Market-data readiness hardening vóór echte fetching**: request logs, provider/source metadata, snapshot timestamps, freshness policy, stale/null handling, geen zero-fill, geen stale last-known-price als verse data en geen analysis unlock op ontbrekende/stale data.
- **Usable-cash contract vóór action-drafts**: geen leveraged buying power als veilige cash; usable cash = beschikbare funds/cash minus pending buys, approved/submitted drafts en user buffer; alle cashcijfers moeten auditeerbaar zijn.
- **AI enforcement foundation vóór beslissingsinvloed**: AI-output moet schema-gevalideerd, evidence-linked en source-grounded zijn met injection/credibility/freshness/risk gates; AI mag geen financiële kerngetallen origineren.
- **Decision Package blijft harde voorwaarde vóór suggesties**: immutable/auditable package met identity, portfolio-state, market-data snapshot, evidence/sources, gate outcomes, model outputs, blockers en expiry/validity-window.
- **Eerste account-mode-aware user-approved broker action flow blijft conservatief**: roadmap noteert LMT-only start; geen market orders, geen brackets/stops/trailing in eerste flow, DAY/GTC alleen als later expliciet ondersteund, user approval + backend safety recheck + IBKR confirmation handshake verplicht.
- **IBKR reply-handshake state machine vóór account-mode-aware broker submission**: minimaal states Draft → Safety checked → User approved → Submitted → Awaiting IBKR reply → Reply confirmed → Working → Filled/Cancelled/Rejected → Reconciled.
- Scope in deze taak blijft documentatie-only; geen runtime-/productcodewijzigingen.

## H) Task 88J roadmap backlog expansion (documentation-only)

Toegevoegd als verplichte implementatieblokken (nog runtime pending):
- data foundation: point-in-time opslag, provider adapters, identity links, freshness/pacing gates;
- feature store: market/macro/event/liquidity/microstructure/ETF features;
- model registry + immutable run/version lineage;
- baseline models: ARIMA/ETS/GARCH/HAR-RV + LightGBM/XGBoost quantile stack;
- quantile+conformal: p10/p50/p90 + CQR + coverage diary;
- AI text-to-feature: FinBERT/FinGPT/structured event tagging;
- AI explanation/RAG: Dutch schema-based uitleg met evidence-only numerics;
- AI dissent challenger: confidence modulation only;

- validation spine: walk-forward, purged CV, CPCV, DSR, PBO, holdout;
- monitoring/drift: PSI/KS, IC decay, CRPS, pinball, retraining triggers;
- Decision Package: immutable evidence/model/gate bundle;
- deterministic suggestion translator (Python rules, AI never decides label);
- account-mode-aware user-approved broker action workflow: future, whole-share/unit + Buy/Sell + Limit + Day-only.

- [x] Task 93 — AssetListing identity foundation verdieping (storage/API/tests/docs), zonder runtime market data/forecast/AI/suggesties/actions/orders.

- [x] Task 94 — Conservatieve AssetListing-to-watchlist readiness wiring (API/tests/docs, read-only): watchlist list/detail response bevat typed AssetListing readiness/status via `ibkr_conid`; missing/unvalidated listings blijven blocked voor market data/analysis/suggesties/action drafts; gevalideerde listing blijft status-only zonder runtime unlock. Geen market-data runtime/fetching/historical/scheduler/forecast/AI/suggesties/Decision Packages/action drafts/orders/fake data toegevoegd.
- [x] Task 95 — Conservatieve market-data readiness AssetListing validation-gate harmonisatie (API/tests/docs, read-only): readiness list/detail tonen nu expliciete typed `asset_listing_gate` (`storage_unavailable`, `missing_ibkr_conid`, `missing_listing`, `unvalidated_listing`, `validated_listing`) met geharmoniseerde NL teksten; missing/unvalidated blijft blocked, validated blijft status-only. Geen storage migratie/tabel en geen runtime market-data fetch/scheduler/forecast/AI/suggesties/Decision Packages/action drafts/orders/fake data.


- Task 96 afgerond: read-only terminologie/contract harmonisatie voor readiness/watchlist/latest-snapshot; geen runtime-uitbreidingen toegevoegd.
- Task 100 afgerond: beperkte product-doc terminologie-audit + tracking-harmonisatie buiten UI/API-inventaris (`docs/product/read-only-readiness-product-doc-terminology-audit.md`), zonder runtime-activatie.
- Task 103 afgerond: conservatieve product-doc consistentie follow-up na Task 102 met check tegen vergrendelde read-only terminology in `locked-decisions.md`; kleine tracking/wordingdrift hersteld en compacte notitie toegevoegd (`docs/product/read-only-readiness-consistency-check-task-103.md`), zonder runtime-activatie.
- Task 104 afgerond: conservatieve documentatie/review-hardening mini-follow-up op post-Task-103 trackingconsistentie tegen `locked-decisions.md`; kleine trackingdrift gecorrigeerd en compacte notitie toegevoegd (`docs/product/read-only-readiness-tracking-consistency-task-104.md`), zonder runtime-activatie.
- Task 105 afgerond: conservatieve documentatie/review-hardening terminology lock check follow-up na Task 104 tegen `locked-decisions.md`; kleine tracking/wordingdrift gericht hersteld (current-state post-Task-104 tracking) en compacte notitie toegevoegd (`docs/product/read-only-readiness-terminology-lock-check-task-105.md`), zonder runtime-activatie.
- Task 106 afgerond: conservatieve documentatie/review-hardening terminology lock discipline follow-up na Task 105 tegen `locked-decisions.md`; kleine tracking/wordingdrift gericht hersteld (current-state titel + samenvattingsregel naar post-Task-105 status) en compacte notitie toegevoegd (`docs/product/read-only-readiness-terminology-discipline-check-task-106.md`), zonder runtime-activatie.
- Task 107 afgerond: conservatieve documentatie/review-hardening sustainability-check na Task 106, inclusief driftcorrectie in current-state en compacte tracking-drift preventieregel in productdocs; geen runtime-activatie.
- Task 108 afgerond: grote non-runtime implementatie-prep audit gedocumenteerd in `docs/product/non-runtime-foundation-preflight-task-108.md`; exact één conservatieve Task 109 geselecteerd (request-log/provider-metadata/freshness-audit storage/API contract preflight, documentatie/design-only), zonder runtime-activatie.
- Volgende conservatieve stap: Task 109 — request-log/provider-metadata/freshness-audit storage/API contract preflight (documentation/design-only, geen runtime unlock).


- [x] Task 98 — Read-only readiness UI/API contractinventaris (documentatie-only): nieuw inventarisdocument voor resterende UI-schermen + API/client contracten met veilige/onveilige labelpatronen en conservatieve follow-up governance; geen runtime market-data/latest-price fetching/scheduler/forecast/AI/suggesties/Decision Packages/action drafts/orders/fake data.


- [x] Task 99 — documentatie/review-guardrail-only: compacte read-only readiness PR-checklist + term-review rubric toegevoegd en gekoppeld in productdocumentatie; geen runtime market-data fetching/latest-price fetching/scheduler/forecast runtime/AI runtime/suggesties/Decision Packages/action drafts/orders/fake data.


- Task 113 afgerond: read-only audit summary/count contracten + usability verbeteringen; geen runtime-unlock.


- Task 114 afgerond: read-only audit linked-record coverage/navigation hardening en web type-alignment; geen runtimegedrag toegevoegd.

- Na Task 123 verschuift focus naar Task 124: read-only open orders/executions sync runtime (manueel, geen orders).
## Task 125B update: durable IBKR sync storage repository layer completed; runtime/API wiring deferred to 125C.

- Task 125D: **completed** — read-only portfolio valuation voorbereiding toegevoegd vanuit duurzame IBKR sync snapshots, met expliciete blocked/control-needed status bij ontbrekende of verouderde marktdata. Geen market-data runtime, geen suggesties, geen action drafts, geen broker orders/execution en geen fake prijzen toegevoegd.


- Task 125H afgerond: FX snapshot durable storage foundation (read-only, no runtime fetch).

- Task 125I voltooid (read-only FX snapshot consumption in valuation readiness); vervolg blijft conservatief zonder runtime provider fetch.


- Task 125L afgerond: read-only wiring van Decimal-only conversion-total calculator in valuation readiness endpoint; alleen opgeslagen inputs, zonder runtime FX/provider fetch, zonder market-data runtime en zonder suggestions/action drafts/orders.
- Task 125N afgerond: read-only web/API-client display support voor valuation conversion totals toegevoegd; bestaande valuation readiness endpoint hergebruikt; simpele Nederlandse labels toegepast; geen browserberekeningen; geen API/runtime/storage changes; geen suggesties/action drafts/orders en geen fake totals.
- Task 125O afgerond: read-only advanced valuation trace/details display toegevoegd; bestaande valuation readiness endpoint hergebruikt; bestaande trace- en blocker fields hergebruikt; simpele Nederlandse labels; geen browserberekeningen; geen API/runtime/storage changes; geen suggesties/action drafts/orders en geen fake totals.
- Task 125O-R afgerond: web build repair-only na Task 125O; geen runtimewijziging.
- Task 125P afgerond: document-first/read-only preflight voor cost-basis en unrealized P/L display rules toegevoegd op basis van opgeslagen IBKR snapshots + bestaande market/FX readiness gates; geen berekeningen, geen API/web UI-behavior changes, geen runtime FX/provider fetch, geen market-data runtime, geen latest-price fetching, geen suggesties/action drafts/orders en geen fake kostbasis/P-L/FX/converted totals.
- Task 125R afgerond: Task 125Q pure Decimal-only cost-basis/unrealized P/L calculator is nu read-only wired in `GET /portfolio/valuation/readiness` met strikte stored-input gates; geen runtime market-data/latest-price fetching, geen runtime FX/provider fetch, geen suggesties/action drafts/orders, geen broker execution en geen fake waarden.
- Task 125R-R afgerond: gerichte mypy Optional Decimal narrowing reparatie na Task 125R; geen API-behavior uitbreiding, geen runtimewijzigingen en geen scopeverbreding.
- Task 125T afgerond: read-only advanced row-level trace/details display voor kostbasis en ongerealiseerde winst/verlies readiness toegevoegd met uitsluitend bestaande API-readiness tracevelden; geen browser-side berekeningen en geen runtime/API/storage/migratie-uitbreiding.
- Task 125U afgerond: document-first review/preflight voor valuation readiness UI-teksten en helpteksten toegevoegd met consistent eenvoudig Nederlands + checklist voor ontbrekende invoer en trace-empty staten; geen runtime/API/web behavior/storage/migraties/fetch/suggesties/action drafts/orders/broker execution/fake waarden.
- Task 125S afgerond: read-only web/API-client display support voor bestaande kostbasis en ongerealiseerde winst/verlies readiness-velden toegevoegd, zonder browser-side berekeningen en zonder runtime/API/storage/migratie-uitbreiding.
- Task 125M afgerond: document-first/read-only UI/API display contract preflight voor valuation conversion totals toegevoegd (`docs/product/valuation-conversion-total-display-contract-preflight-task-125m.md`); geen web UI behavior changes, geen API behavior changes, geen runtime FX/provider fetch, geen market-data runtime, geen suggesties/action drafts/orders en geen fake FX-rates/converted totals.

## Workflow update na Task 130P
- Manual owner-testing verschuift naar volledige Version 1 release candidate.
- Partial feature-slices vereisen CI + fake-adapter/fixture/contracttestdekking.
- Kleine Task 131 is vervangen door Task 131B als volgende veilige Milestone B batch.

- Task 130Q — **completed (documentation-only)**: owner workshop product decision locks vastgelegd + tracking marker drift hersteld; geen runtimewijzigingen.
- Task 130Q-R — **completed (documentation/process-helper repair-only)**: current-state marker drift na Task 130Q hersteld en `scripts/check_product_tracking.py` verhard voor suffix-task markers (`130`/`130P`/`130Q`/`130Q-R`); geen runtimewijzigingen.

- [x] Task 138-R — Repair-only: API pytest regressie na Task 138 hersteld; timeout/provider adapterfouten rapporteren nu `payload_validation_status=not_attempted` i.p.v. `passed`; adapter/runtimefouten blijven gescheiden van payloadvalidatiefouten; geen runtimeverbreding, geen storage schema/migraties, geen echte TWS/Gateway runtime, geen market-data runtime, geen suggesties/action drafts/orders.

- Task 139 afgerond: read-only IBKR sync history/diagnostics verdiept; geen runtime-verbreding naar echte brokerconnectiviteit of orders.

- Task 145 afgerond: manual IBKR read-only runtime boundary met fake-client tests only; blijft disabled-by-default en order/suggestie/action safety blijft geblokkeerd.

- Task 153-L completed (docs/product-lock recovery).
- Task 155 queued: real IBKR account-mode-aware read-only account snapshot preflight for cash and positions without persistence/valuation and without market-data/FX/suggestions/action drafts/orders.
