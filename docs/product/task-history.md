- Task 171 completed: QVM factor predictor + EODHD fundamentals fetcher + storage (Slice 16 of the V1 expansion queue, third step of §21.4). Migration `0038_asset_fundamentals_snapshots` + `AssetFundamentalsSnapshotRecord` + `SqlAlchemyAssetFundamentalsSnapshotRepository`. `EodhdClient.fetch_fundamentals` + `EodhdFundamentals` dataclass + `_parse_fundamentals` reading General/Highlights/Valuation/Technicals. `QvmFactorPredictor` (pure Python) implementing `PredictorProtocol`: Quality + Value + Momentum cross-sectional z-scores combined into a composite, mapped to ±25% annualised drift. Universe injected via `UniverseFundamentals` fixture; Slice 17 wires the scan. Locked blocking reasons + safety booleans hard-False.
- Task 170 completed: Mean-reversion predictor + deterministic ensemble combiner (Slice 15 of the V1 expansion queue, second step of §21.4). `MeanReversionPredictor` combines RSI(14) + Bollinger z (20) + Hurst exponent (multi-window R/S over 100d) into a pull factor that moves the projected price toward the 20-day SMA. `compute_ensemble_forecast(predictors, inputs, weights)` runs every predictor, drops blocked ones, combines via weighted averages, derives direction from combined expected return, and multiplies confidence by an agreement factor. Returns `EnsembleResult` with per-predictor `EnsembleContribution` breakdown for the Diary. Pure Python; no orchestrator change yet.
- Task 169 completed: `PredictorProtocol` + Momentum predictor (Slice 14 of the V1 expansion queue, first concrete step of §21.4). New `predictor_protocol` module locks the input/output contract; `GbmPredictor` adapts the existing baseline; `MomentumPredictor` combines 12-1 + time-series momentum into a `PredictionDistribution`. No orchestrator change yet — Slice 15 wires the combiner. Tests cover the protocol invariants, GBM wrapping, momentum signal direction, deterministic output, and drop-in-shape with GBM.
- Task 168 completed: doctrine relock + APScheduler skeleton (Slice 13 of the V1 expansion queue). Relaxes the `account_mode_mismatch` dry-run failure, the `version1_paper_only` readiness blocker and the `ibkr_expected_environment` order-submission factory gates per §21.1. New `GET /ibkr/account/mode` endpoint reports the detected mode (PAPER / LIVE / UNKNOWN) for the dashboard badge. Storage migration `0037_scheduler_runs` + `SchedulerRunRecord` + repository. `apscheduler.BackgroundScheduler` wired into the FastAPI lifespan behind `scheduler_enabled` (default False); daily_briefing job is a skeleton callable replaced in Slice 21. `run_daily_briefing_job(...)` captures every fire as an audit row with running → succeeded/failed transitions. Two new routes `GET /scheduler/jobs` + `GET /scheduler/runs/latest`. Web: PAPER / LIVE badge in the Portefeuille header + new "Scheduler" panel. Disabled-by-default; manual approval gate stays; safety booleans hard-False.
- Task 167 completed: deterministic daily briefing + alert digest end-to-end (Slice 12). New storage migration `0036_daily_briefings` adding `daily_briefings` (UNIQUE per date) + `briefing_alerts` (append-only). `DailyBriefingRecord` + `BriefingAlertRecord` dataclasses with safety-False invariants. Pure-Python `daily_briefing` module in `packages/portfolio` with typed `BriefingInputs` and deterministic `compute_daily_briefing(...)` — items counted only when at-or-after `lookback_started_at`; new suggestions/packages/drafts emit info alerts (failed dry-run drafts → warning); diary outcomes + critical state events → info / critical alerts; stale FX → warning. AI never authors the summary. `daily_briefing_sync.generate_daily_briefing(...)` orchestrator + `POST /briefings/daily/compute` + `GET /briefings/daily/latest`. New settings `daily_briefing_sync_enabled` / `daily_briefing_lookback_hours`. Portefeuille page renders a Dagbriefing panel. Disabled-by-default; safety booleans hard-False; no broker action.
- Task 166 completed: Belgian tax module wired into the action draft Orderimpact (Slice 11). New pure-Python `belgian_tax` module in `packages/portfolio` with locked TOB rates and per-transaction caps + 30% dividend roerende voorheffing. `compute_tob(*, transaction_value, security_class)` + `compute_dividend_withholding(*, gross_dividend)` + `TobSecurityClass` enum (standard_stock / distributing_etf / accumulating_etf / bond / sicav_redemption / other). Extended `Orderimpact` + `compute_orderimpact(..., belgian_tob_security_class=...)` to thread the TOB through. Migration `0035` adds `estimated_belgian_tob` + `belgian_tob_security_class` columns to `asset_action_drafts`; `AssetActionDraftRecord` carries both with non-negative invariant. Orchestrator persists the TOB; serializer surfaces it; Portefeuille Action drafts table gains a "TOB (BE)" column. Informational only — TOB does not change order sizing. No broker execution; no AI; safety booleans hard-False on every row.
- Task 165 completed: AI explanation layer (RAG read-only) end-to-end (Slice 10). New storage migration `0034_decision_package_explanations` adding two tables (`decision_package_explanations` with UNIQUE per package version + `explanation_evidence_ledger` append-only audit). Pure-Python `ai_explanation_guards.validate_explanation_output(...)` in `packages/portfolio` enforces the V1 doctrine: no number in the output that isn't in the input (locale-aware numeric tokenizer for thousand-separators + Dutch decimal commas), locked Dutch risk disclaimer required, max-length + empty checks. New `ai_explanation_provider` boundary in `apps/api` with `StubExplanationProvider` (deterministic paraphrase, no network); `build_explanation_provider(settings)` returns the stub only when explicitly enabled; real providers return `ExplanationProviderUnavailable` until a future slice. `ai_explanation_sync.generate_explanation(...)` builds a canonical input JSON, hashes it, calls the provider, validates the output, persists the explanation + one ledger entry per evidence source. New routes `POST` + `GET /decision-packages/{id}/explanation`. New settings: `ai_explanation_enabled` / `ai_explanation_real_client_enabled` / `ai_explanation_provider_code` / `ai_explanation_max_output_chars`. Portefeuille Decision Package card renders an AI uitleg subsection with generate + read buttons and blocked-reason warning. Disabled-by-default; AI never originates a number; safety booleans hard-False on every persisted row.
- Task 164 completed: Research Desk runtime wired into the Decision Package evidence chain (Slice 9). New storage migration `0033_decision_package_research_evidence` adding five nullable columns (`research_evidence_count`, `research_credibility_summary`, `research_freshness_status`, `research_blocking_reason`, `research_snippet_nl`). Pure-Python `research_evidence_summary` in `packages/portfolio` with deterministic credibility/freshness aggregation + locked blocking reasons (`prompt_injection_high_risk`, `credibility_rejected`); AI never assigns the summary. New `build_research_summary_by_symbol(...)` helper in `decision_package_sync` collects per-asset research from the existing `SqlAlchemyResearchSourceArchiveRepository`. `sync_decision_packages(...)` now threads the summary through to `_AssemblyContext` and into the immutable record; the content_hash includes the four scalar research fields so versioning correctly reflects research changes. `POST /decision-packages/compute` builds the summary just before invoking the orchestrator. Portefeuille page renders a Research subsection per Decision Package card. Disabled-by-default; research evidence can block but never auto-promote.
- Task 163 completed: reconciliation + Prediction Diary end-to-end (Slice 8). New `prediction_diary_entries` table (migration 0032, UNIQUE on `suggestion_id`, safety booleans hard-False), `PredictionDiaryEntryRecord` + `SqlAlchemyPredictionDiaryRepository`. Pure-Python `prediction_diary_eval` in `packages/portfolio` returning deterministic horizon labels (right/wrong/early/inconclusive/no_data). `reconciliation_sync.reconcile_submissions(...)` matches submissions against the latest IBKR open-orders + executions, transitions FILLED/CANCELLED/REJECTED and auto-advances to RECONCILED in one pass with a `critical`-severity event per transition; the state machine guards every move via `require_transition_allowed`. `prediction_diary_sync.evaluate_prediction_diary(...)` builds one diary row per suggestion using the linked forecast + persisted EOD bars (7-day walk-back across weekends). New routes `POST /action-drafts/reconcile`, `POST /prediction-diary/evaluate`, `GET /prediction-diary`. Disabled-by-default; no auto-execution; AI never assigns the outcome label; `safe_for_self_learning` / `safe_for_model_retraining` / `safe_for_orders` / `safe_for_broker_submission` remain hard-False on every record and every response.
- Task 162 completed: user-approved IBKR paper submission with the locked state-machine handshake (Slice 7). New `action_draft_state_machine` in `packages/portfolio` (locked 13-state graph, only forward + edit-revokes-approval transitions), new `asset_action_draft_submissions` + `asset_action_draft_events` tables (migration 0031, safety booleans hard-False), real `IbapiOrderSubmissionClient` paper-only placeOrder helper (LMT/DAY/whole-share STK), `build_real_order_submission_client` factory gated five ways, `action_draft_submission` orchestrator with `approve_action_draft(...)` + `submit_action_draft_to_paper(...)`, new routes `POST /action-drafts/{id}/approve` + `POST /action-drafts/{id}/submit-to-ibkr-paper` + `GET /action-drafts/{id}/status`. First slice that can actually send a paper order — disabled-by-default, paper-only, no auto-submission, critical event per state transition.
- Task 161 completed: action draft skeleton + Orderimpact + dry-run end-to-end (Slice 6). Pure-Python `action_draft_safety` in `packages/portfolio` (sizing, Orderimpact, deterministic dry-run failure codes), new `asset_action_drafts` table (migration 0030) + `AssetActionDraftRecord` (rejects non-LMT / non-DAY / non-BUY-SELL / non-positive quantity-or-price / any safety-flag-set-True) + `SqlAlchemyAssetActionDraftRepository`, `action_draft_sync.generate_action_drafts(...)` orchestrator filtering to actionable labels and persisting one draft per Decision Package, new routes `POST /action-drafts/compute` + `GET /action-drafts/latest` + `GET /action-drafts/{draft_id}`, Portefeuille Action drafts table with Orderimpact preview and dry-run badge. Disabled-by-default; **still no submission**; every safety boolean hard-False.
- Task 160 completed: Decision Package foundation end-to-end (Slice 5). Immutable, content-hashed bundle per (conid, generated_at) in `asset_decision_packages` (migration 0029) + matching `AssetDecisionPackageRecord` + insert-only `SqlAlchemyAssetDecisionPackageRepository`. `decision_package_sync.sync_decision_packages(...)` orchestrator bundles position/cash/market/FX/forecast/suggestion + gate outcomes + audit links + Dutch rationale; SHA-256 hash anchors the evidence. New routes `POST /decision-packages/compute`, `GET /decision-packages/latest`, `GET /decision-packages/{conid}/latest`. Portefeuille page grows a collapsible Decision Packages section with full denormalised evidence per package. Disabled-by-default; the package is the hard prerequisite gate before any action draft can exist (no drafts in this slice); no orders, no broker submission, no AI authoring; safety booleans hard-False on every persisted row.
- Task 159 completed: deterministic Dutch label translator + Suggestions foundation end-to-end (Slice 4). `baseline_label_translator` in `packages/portfolio` maps `BaselineForecast` + risk profile + held/cold context to one of the 10 locked action labels — Python rules over evidence-gated inputs only; AI never decides. New `asset_suggestions` table (migration 0028) + `AssetSuggestionRecord` + `SqlAlchemyAssetSuggestionRepository`. `suggestion_sync.sync_suggestions(...)` orchestrator, `POST /suggestions/compute` + `GET /suggestions/latest` routes, "Actie" badge column on the Portefeuille positions table. Disabled-by-default; no action drafts, no orders, no broker execution, no AI runtime; safety booleans hard-False on every persisted row.
- Task 158 completed: baseline forecast engine end-to-end (Slice 3, V1.1 stage). Pure-Python lognormal GBM forecaster in `packages/portfolio.baseline_forecast` (p10/p50/p90 + probability mass + annualized vol + downside risk + confidence), new storage migration `0027_market_data_bars_and_asset_forecasts` with two tables and matching repositories, `EodhdClient.fetch_eod_bars(...)`, `forecast_sync.sync_forecasts(...)` orchestrator, new routes `POST /forecasts/compute` + `GET /forecasts/latest`, and a "Verwachte richting (1m)" badge on the Portefeuille positions table. Disabled-by-default; no AI, no suggestions, no action drafts, no orders, no broker execution; safety booleans hard-False on every persisted row.
- Task 157 completed: real market-data + FX provider (EODHD), end-to-end (Slice 2). Added `EodhdClient` (stdlib `urllib`, injectable HTTP backend), `market_data_sync.sync_market_data_and_fx` orchestrator with IBKR→EODHD exchange suffix mapping + automatic FX-pair derivation, `build_market_data_provider` factory, and `POST /market-data/sync` route. Persists into the existing `MarketDataLatestSnapshotRecord` + `FxRateSnapshotRecord` tables so the existing valuation readiness consumer surfaces real `Marktwaarde` and unrealized P/L. Disabled-by-default; no orders/suggestions/action drafts/broker execution/schema migrations/scheduler runtime added.
- Task 156 completed: real IBKR paper read-only sync runtime (Slice 1). Added `IbapiReadOnlySyncClient` (real `ibapi`-backed adapter for cash/positions/open-orders/executions), `build_real_sync_adapter` factory gated on `ibkr_sync_real_client_enabled` + paper-mode + readonly + host/port/client-id, and wired the factory into `POST /ibkr/sync/run` with a context-managed `close()`. Disabled-by-default; tests use an injected fake `ibapi` app driving the shared production callback set (no socket opens in CI). No orders/suggestions/action drafts/market-data/FX runtime added; readiness gate and persistence path unchanged.
- Task 152-R6 completed: repair-only merged-red CI fix after Task 152-R5 for the `api` job `pytest` failures; fake-client execution helpers now enable the full Task 152 prerequisite gate set in tests, including dummy `ibkr_sync_host`, `ibkr_sync_port`, and `ibkr_sync_client_id` values alongside `ibkr_tws_readonly_real_client_enabled=True`. Missing host/port/client-id blockers remain tested for default/real configuration gaps, default-blocked tests still verify disabled-by-default safety-gated behavior, no-secret checks remain strict (no raw config/account payload leaks), and no production runtime behavior was widened (runtime default-disabled, readiness never connects, no sync/market-data/FX/suggestions/actions/orders/broker execution, no auto-connect/reconnect/persistent session manager, no schema/migrations, no `ib_insync`).
- Task 152-R5 completed: repair-only merged-red CI fix after Task 152-R4 for the `api` job `pytest` failures; fake-client execution helpers now enable the full Task 152 gate set including `ibkr_tws_readonly_real_client_enabled=True`, and remaining fake-client execution/error-path tests that still used `_settings(...)` were corrected to use `_fake_client_ready_settings(...)`. Default-blocked tests still prove disabled-by-default and safety-gated behavior. No production runtime widening: runtime remains disabled by default, readiness endpoint never connects, no account/portfolio sync, no positions/cash/open-orders/executions sync, no market-data runtime, no FX runtime, no suggestions/action drafts/orders/broker execution, no auto-connect/reconnect loop, no persistent session manager, no schema/migrations, no `ib_insync`, and no secret/raw broker payload exposure.
- **Task 152-R4 (repair-only, completed):** Repaired merged-red CI after Task 152-R3 in `api` job at step `pytest` (with `ruff` and `mypy` already green). Root cause was stale fake-client manual status-check expectations after Task 152 gate tightening. Repaired by adding focused fake-client-ready settings helpers and updating only fake-client execution-path tests to enable required gates before expecting connect/check/disconnect behavior. Kept default-blocked/status-check-disabled tests unchanged. Refined no-secret assertions to reject exact raw configured values (host/port/client ID/account ID) while allowing safe diagnostic code names like `missing_host`, `missing_port`, `missing_client_id`. No runtime widening: real manual status-check capability remains, runtime disabled by default, readiness never connects, no sync/market-data/FX/suggestions/action drafts/orders/broker execution, no auto-connect/reconnect/persistent session manager, no schema/migrations, no `ib_insync`.
- **Task 152-R2 (repair-only, completed):** Repaired merged-red CI after Task 152-R in `api` job (`ruff check .`) by replacing constant-attribute `getattr(...)` (`EClient`/`EWrapper`) with Ruff-compliant direct attribute access via narrow local Any-casts in the manual `ibapi` status client, while preserving the typed `ibapi` protocol/factory boundary, fake-client testability, and real manual status-check capability. Runtime remains disabled by default; readiness endpoint still never connects; no sync/market-data/FX/suggestions/action drafts/orders/broker execution, no auto-connect/reconnect/persistent session manager, no schema/migrations, no `ib_insync`, and no API/web behavior changes beyond existing manual status endpoint/readiness behavior.
- **Task 152-R (repair-only, completed):** Repaired merged-red CI after Task 152 in `api` job (`mypy src`) by isolating untyped `ibapi` imports/subclassing behind typed protocol/factory boundary for manual status client while keeping real manual status-check behavior unchanged and safety/runtime boundaries intact.
- Task 151: dependency-isolated `ibapi` façade toegevoegd (preflight-only, geen connectiviteit/wiring/runtimeuitbreiding).
- Task 150-R completed: merged-red repair na Task 150 voor API `pytest` failure in `test_repository_does_not_introduce_ib_insync`; preflightscan vernauwd naar projectmetadata + productie-runtime broncode i.p.v. alle repository-testbestanden, zodat bestaande safety-assertions met `ib_insync` in tests (zoals `packages/storage/tests/test_alembic_skeleton.py`) geen vals-positieve dependencyintroductie meer triggeren. `ibapi` blijft dependency/install-import preflight-only, geen productie-runtime import van `ibapi`, geen `ib_insync` dependency, geen runtime-connectiviteit/sockets by default, geen echte TWS/Gateway clientimplementatie, geen auto-connect/reconnect/persistente session manager, geen account/portfolio sync runtime, geen market-data/FX runtime, geen suggestions/action drafts/orders/broker execution, geen API/web-gedragswijziging en geen storage schema/migraties.
- Task 150 completed: selected `ibapi` dependency toegevoegd in `apps/api/pyproject.toml` voor dependency/install/import CI preflight; import smoke test toegevoegd in `apps/api/tests/test_ibkr_client_dependency_preflight.py` met no-socket guard op import. Geen productie-runtime import van `ibapi`, geen `ib_insync`, geen runtime-connectiviteit, geen echte TWS/Gateway clientimplementatie, geen auto-connect/reconnect/persistente session manager, geen account/portfolio sync runtime, geen market-data/FX runtime, geen suggestions/action drafts/orders/broker execution, geen API/web-gedragswijziging en geen storage schema/migraties.
- Task 149 completed: IBKR client dependency-selectie compatibiliteitspreflight (documentatie/preflight-only) toegevoegd; `ibapi` en `ib_insync` vergeleken zonder runtime-connectiviteit; geen runtime/API/web/storage-schemawijzigingen en geen dependency-introductie in projectmetadata. Aanbevolen vervolg: Task 150 dependency-only CI install/import preflight met voorkeur `ibapi`.
- Task 148 — Completed (documentation/planning/decision-gate only): real-runtime implementatiebeslissings-gate vastgelegd vóór introductie van TWS/Gateway client dependency; vergelijking `ibapi`/`ib_insync`/dependency-free/defer + acceptatiecriteria/rollback/next-task. Geen runtime code/API/web/storage/migraties/dependencies/connectiviteit toegevoegd.
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
- Completed: repair-only fix na merged-red Task 140 voor API mypy-failure in `status_routes.py` (`IbkrSyncRunRecord` heeft geen payload-validatievelden).
- Durable reconciliatie gebruikt nu conservatieve fallback voor payload-validatie-details (`not_available`, `Niet beschikbaar`, en NL helptekst dat details niet opgeslagen zijn).
- Geen storage schemawijzigingen/migraties; geen echte TWS/Gateway runtime; geen persistente session manager; geen market-data runtime; geen FX runtime; geen suggesties, action drafts of orders toegevoegd.

## Task 140
- Completed: read-only reconciliation readiness endpoint toegevoegd (`GET /portfolio/valuation/reconciliation-readiness`) die bestaande waarderingblockers samenvat zonder waarden te verzinnen en met alle order/suggestie/action safetybooleans geblokkeerd. Geen TWS/Gateway runtime, geen session manager, geen schema/migraties, geen market-data/FX runtime, geen suggesties/action drafts/orders/execution.

- Task 138-R: **completed** — repair-only na merged-red Task 138 (`api` job, `pytest` stap): `test_timeout_adapter_failure_is_not_validation_failure` en `test_provider_adapter_failure_is_not_validation_failure` gerepareerd door adapter timeout/provider-foutpaden in `run_sync(...)` `payload_validation_status` op `not_attempted` te laten (niet `passed`). Adapter/runtimefouten blijven gescheiden van payloadvalidatiefouten. Geen runtime-scope toegevoegd: geen echte TWS/Gateway runtime, geen persistente session manager, geen storage schema/migraties, geen market-data runtime, geen suggesties/action drafts/orders/broker execution.
- Task 138: completed — hardened IBKR read-only adapter contracts and deterministic fake-adapter sync fixtures for cash, positions, open orders and executions; tests now explicitly separate adapter/runtime failures (`timeout`, `provider_error`) from payload validation failures (`payload_validation_failed`) and readiness blocking statuses. No real TWS/Gateway runtime, no persistent session manager, no storage schema/migrations, no market-data runtime, no suggestions/action drafts/orders/broker execution added.
## Task 137
- Completed: planning/documentation-only Milestone B sliceselectie na Task 136 met kandidaatvergelijking, risicobeoordeling en selectie van één volgende milestone-sized implementatietaak.
- Toegevoegd: `docs/product/milestone-b-next-implementation-slices-task-137.md` als source-of-truth selectiedocument.
- Geselecteerd als volgende implementatietaak: **Task 138** (IBKR read-only adaptercontract + deterministic fake-adapter fixture hardening batch).
- Niet toegevoegd: runtimecode, API/web gedragwijziging, storage schema/migraties, echte TWS/Gateway runtime, market-data runtime, suggesties, action drafts, orders of broker execution.

## Task 136
- Doel: durable IBKR sync status read model contract uitlijnen met Task 135B payload-validatie/safety response shape.
- Resultaat: `serialize_sync_status_record(...)` retourneert nu payload-validatievelden met conservatieve `not_available` defaults voor durable historische runs zonder opgeslagen validatiedetails, plus volledige safety booleans (`actions_allowed/order_* /suggestions_allowed/can_submit_orders/safe_for_orders/blocks_orders`) in geblokkeerde toestand.
- Scopebewaking: geen storage schema/migraties, geen runtimeverbreding, geen echte TWS/Gateway runtime, geen market-data runtime, geen suggesties/action drafts/orders/broker execution toegevoegd.

## Task 135B-R
- Status: afgerond (repair-only).
- Doel: merged-red Task 135B CI-fout herstellen in API job (`ruff check .`, E501 line-too-long).
- Resultaat: API Ruff E501 in `ibkr_sync.py`, `ibkr_sync_validation.py` en gerelateerde tests multiline geformatteerd zodat lint voor deze foutklasse passeert; geen feature-uitbreiding.
- Checks: Ruff pass; lokale mypy/pytest in deze omgeving geblokkeerd door ontbrekende dependencies (`fastapi`/package stubs).
- Scopebehoud: geen runtime/API-contractwijziging, geen storage schema/migraties, geen market-data runtime, suggesties, action drafts, orders of broker execution toegevoegd.

- Task 135A: completed — documentation-only audit/reconciliatie van repository/product-state na PR #326 (Task 134B-R2): producttrackingdrift gecorrigeerd in current-state marker, task-queue Milestone B volgorde, backlog next-up, handover/scope/next-task alignment en nieuw auditdocument met statusclassificatie. Geen runtime-, API-, web-, storage-, migratie- of netwerkgedrag gewijzigd; Task 135B blijft volgende implementatietaak.
- Task 134B-R2: completed — Task 134B-R2 repaired the remaining API pytest failures after merged Task 134B-R by preventing readiness recomputation in the final `run_sync(...)` response: readiness was first computed with the injected session-status adapter, then incorrectly recomputed by `read_status(settings)` without that adapter; `run_sync(...)` now returns status using the same precomputed readiness object. No real TWS/Gateway network runtime, no real IBKR account/portfolio sync runtime, no market-data runtime, no suggestions, no action drafts, no Decision Packages runtime, no orders, no broker execution, no financial calculations and no fake data were added.
- Task 134B-R: completed — repaired API pytest failures after merged Task 134B by fixing incomplete test settings on the session-status side of the readiness gate in `apps/api/tests/test_ibkr_sync_endpoints.py` (`_base_settings` now includes required sync + session-status defaults and remains override-safe). No production runtime behavior change beyond test/config repair; no real TWS/Gateway network runtime, real IBKR account/portfolio sync runtime, market-data runtime, suggestions, action drafts, Decision Packages runtime, orders, broker execution, financial calculations, or fake data added.
- Task 134B: completed — readiness/preflight gate wired into manual sync execution blocking; blocked/needs-control prevents adapter calls and persistence; explicit ready paper test seam keeps injected fake adapter paths test-only; no real network/sync/market-data/suggestions/actions/Decision Packages/orders/broker execution/financial calculations/fake data added.
## Task 133B-R
- Completed: product-tracking drift repair voor ontbrekende Task 133B scope-register trackingnotitie.
- Updated: `docs/product/version-1-scope-register.md` aangevuld en producttrackingdocs geharmoniseerd zonder runtimewijzigingen.
- Hardened: `scripts/check_product_tracking.py` verifieert nu dat de nieuwste completed task uit `current-state.md` ook in `task-history`, `version-1-backlog` en `version-1-scope-register` staat.
- Scope guard: documentation/process-helper only; geen runtime/API/web/storage/migratie/sync/market-data/FX/suggesties/action drafts/Decision Packages/orders/broker execution/financiële berekeningen/fake data.

## Task 133B
- Completed: minimale IBKR read-only sync readiness/preflight status gate toegevoegd met pure readiness builder + status exposure op `GET /ibkr/sync/status`.
- Readiness voegt statuslabels/reasons toe (`blocked`, `needs_control`, `ready_for_manual_readonly_sync`) met conservatieve safety booleans en zonder runtime-unlock.
- Niet toegevoegd: geen real TWS/Gateway network runtime, geen account/portfolio sync runtime, geen market-data runtime, geen suggesties/action drafts/orders/broker execution, geen financiële berekeningen en geen fake data.

## Task 132B
- Completed: document-first selectie en afbakening van de volgende veilige Milestone B IBKR read-only sync foundation batch na Task 131B/131B-R.
- Toegevoegd: `docs/product/ibkr-read-only-sync-foundation-batch-selection-task-132b.md` met foundation-inventaris, gap-analyse, kandidaatvergelijking en batchselectie.
- Geselecteerd: Task 133B (IBKR read-only sync readiness/preflight gate op basis van Task 131B account/session status outputs).
- Niet toegevoegd: runtime/API/storage/migratie/netwerk/sync/market-data/suggesties/action drafts/orders/broker execution/financiële berekeningen/fake data.

## Task 131B-R
- Completed: repair na merged Task 131B voor API pytest-regressie waarbij `account_mode_status` `unknown` teruggaf i.p.v. `mismatch` in wrong-account-mode pad zonder expliciete `account_mode`.
- Hersteld: statusnormalisatie bewaart expliciete adapter-`mismatch`, forceert `mismatch` bij `connected_wrong_account_mode`, en behoudt veilige blokkades/booleans.
- Niet toegevoegd: nieuwe runtime scope; geen echte IBKR-netwerkadapter, auto-connect, sync, market-data runtime, suggesties/action drafts/Decision Packages runtime, orders/broker execution, financiële berekeningen of fake data.

## Task 131B
- Completed: IBKR read-only account/session safety batch op Task 130 boundary met account-mode mapping, unknown-status veilige wording, mappings voor connection_failed/authentication_required/pacing_limited, adapter-exception safety, fake-adapter tests en no-secret/no-fake-data checks.
- Niet toegevoegd: echte IBKR-netwerkadapter, auto-connect, sync runtime, market-data runtime, suggesties/action drafts/Decision Packages runtime, orders/broker execution, financiële berekeningen of fake data.

## Task 130Q-R — Repair current-state marker drift and suffix-task tracking

- Status: afgerond (documentation/process-helper repair-only).
- Gefixt: `docs/product/current-state.md` marker gecorrigeerd naar `Huidige toestand: **na Task 130Q-R**` om drift na Task 130Q te verwijderen.
- Verharding: `scripts/check_product_tracking.py` vergelijkt taskmarkers nu op `(nummer, suffix, repair-suffix)` zodat `130 < 130P < 130Q < 130Q-R < 131B` correct wordt gedetecteerd.
- Producttrackingdocs bijgewerkt (`task-history`, `version-1-backlog`, `version-1-scope-register`) met Task 130Q-R completionnotitie.
- Bevestigd: geen runtime/API/web/storage/migratie/sync/market-data/FX/suggestie/action-draft/order/broker execution/financiële-calculatie wijzigingen.

## Task 130Q — Record owner workshop Version 1 product decision locks

- Status: afgerond (documentation/product-planning-only).
- Toegevoegd: `docs/product/version-1-owner-workshop-decision-locks-task-130q.md` als source-of-truth lock voor daily operating model, mission-control dashboard (`AI Trading Agent`), structured order drafts met `Waarom?`, Action Center-flow, `Orderimpact`, Research Desk/Onderzoeksdesk en `Nieuwe kansen` gates.
- Productdocs uitgelijnd op deze locks; `next-task.md` blijft Task 131B.
- Trackingdrift hersteld in `docs/product/current-state.md` met marker-update en Task 130Q completion-update.
- Bevestigd: geen runtime/API/storage/migration/calculation/suggestion/action-draft/order/broker execution wijzigingen.

## Task 130P — Release-candidate testing and batch-task policy

- Status: afgerond (documentation/process-only).
- Verankerd: owner manual testing alleen op volledige Version 1 release candidate; partial slices via CI/fake adapters/fixtures/contracttests.
- Richtlijn: veilige milestone-batches prefereren binnen safety boundaries.

## Task 129 — Select and document the next Milestone B implementation slice

- Status: afgerond (documentation/planning-only).
- Toegevoegd: `docs/product/milestone-b-ibkr-read-only-runtime-slice-selection-task-129.md` met IBKR foundation-inventaris, kandidaat-slices, selectie en acceptance criteria voor Task 130.
- Geselecteerd als volgende implementatietaak: Task 130 (disabled-by-default IBKR TWS/Gateway read-only session-status adapter boundary + API status exposure).
- Bevestigd: geen runtime productgedrag gewijzigd; geen API behavior, storage, migraties, runtime fetch, berekeningen, suggesties, action drafts, orders, broker execution of fake waarden toegevoegd.

- Task 130 afgerond: disabled-by-default IBKR read-only session-status adapter boundary + API status exposure; geen auto-connect, geen sync, geen market-data runtime, geen suggesties/action drafts/orders en geen credentials/secrets in response.

## Task 128-R — Repair workflow-acceleration product tracking drift

- Status: afgerond (documentation/process-helper repair-only).
- Gefixt: stale marker in `docs/product/current-state.md` bijgewerkt naar `Huidige toestand: **na Task 128**`.
- Verharding: `scripts/check_product_tracking.py` detecteert nu stale `Huidige toestand` markers wanneer de marker achterloopt op de eerste completed task in `current-state.md`.
- Bevestigd: `docs/product/next-task.md` blijft op Task 129; Task 129 is niet gestart.
- Niet gewijzigd: runtime productgedrag, API, web runtime, storage, migraties, runtime fetch, berekeningen, suggesties, action drafts, orders, broker execution of fake waarden.

## Task 128 — Codex workflow acceleration + Version 1 milestone queue

- Status: afgerond (process/documentation-only).
- Toegevoegd: workflow acceleration docs, herbruikbare Codex task template, red/green CI workflowdocument, Version 1 milestone plan en milestone-gebaseerde `task-queue.md`.
- Toegevoegd: kleine stdlib-only lokale helper scripts voor producttracking check en lokale statusweergave.
- Trackingpivot: oude Task 125W micro-auditrichting bewust gedeferreerd/vervangen door Task 128.
- Niet gewijzigd: runtime productgedrag, API, storage, migraties, runtime fetch, berekeningen, suggesties, action drafts, orders, broker execution of fake waarden.

## Task 125V — apply wording catalog op read-only valuation readiness UI labels/helpteksten
- Status: afgerond.
- Toegevoegd: Task 125U wording-catalogus toegepast op bestaande read-only valuation readiness UI-oppervlakken in dashboard/portefeuille/trace-details met eenvoudige Nederlandse labels/helpteksten en duidelijkere unavailable-fallbacks.
- Grenzen bewaakt: alleen UI copy/helptekst/fallback tekst; geen API-behavior, geen storage/migraties, geen runtime fetch, geen browser-side financiële berekeningen of JavaScript money/P&L parsing, geen suggesties/action drafts/orders/broker execution en geen fake waarden.

## Task 125U — document-first review read-only valuation readiness UI-teksten/helpteksten
- Status: afgerond.
- Toegevoegd: nieuw preflight/reviewdocument `docs/product/portfolio-valuation-readiness-ui-text-review-task-125u.md` met UI-tekstinventaris, wording-principes, standaard wording-catalogus, veilige/onveilige voorbeelden en implementatiechecklist.
- Toegevoegd: expliciete checklist voor missing-input-, blocked/control-needed- en trace-empty/onleesbare staten.
- Grenzen bewaakt: documentatie-only; geen runtime code, geen API/web runtime behavior changes, geen storage/migraties, geen runtime fetch, geen suggesties/action drafts/orders, geen broker execution en geen fake waarden.

## Task 125T — read-only advanced kostbasis en ongerealiseerde winst/verlies trace/details display
- Status: afgerond.
- Toegevoegd: row-level detailsweergave in de Portefeuille-sectie `Kostbasis en winst/verlies` met eenvoudige Nederlandse labels voor controle/herkomst, ontbrekende invoer en tracevelden.
- Toegevoegd: type-alignment in web API-client met het bestaande Python API-model (`PositionValuationReadinessRow`), inclusief nullable velden en removal van niet-bestaand `account_ref` als row key-bron.
- Grenzen bewaakt: alleen bestaande readinessvelden en trace-objecten getoond, geen browser-side financiële berekeningen, geen API-behavior changes, geen storage/migraties, geen runtime market-data/latest-price/FX-provider fetch, geen suggesties/Decision Packages/action drafts/orders, geen broker execution en geen fake waarden.

## Task 125S — read-only kostbasis en ongerealiseerde winst/verlies display
- Status: afgerond.
- Toegevoegd: web API-client typecontract uitgebreid met row-level readinessvelden en `rows` in `PortfolioValuationReadinessResponse`.
- Toegevoegd: read-only tabel op de Portefeuille-pagina die alleen bestaande readiness-row velden toont voor kostbasis en ongerealiseerde winst/verlies.
- Grenzen bewaakt: uitsluitend API-provided strings + availability booleans, geen browser-side financiële berekeningen, geen API-behavior changes, geen storage/migraties, geen runtime market-data/latest-price/FX-provider fetch, geen suggesties/Decision Packages/action drafts/orders, geen broker execution, geen fake waarden.

## Task 125Q — pure Decimal-only cost-basis and unrealized P/L calculator (no wiring)
- Status: afgerond.
- Toegevoegd: pure calculator module `packages/portfolio/src/portfolio_outlook_portfolio/valuation_cost_basis_pl.py` met deterministische statusuitkomsten en Decimal-only berekening op caller-provided opgeslagen inputs.
- Toegevoegd: unit tests `packages/portfolio/tests/test_valuation_cost_basis_pl.py` voor kostbasis/P-L ready, ontbrekende average cost, ontbrekende market value, short-positie blokkade, Decimal exactness en geen zero-fallback.
- Niet toegevoegd: API wiring, endpoint contractwijziging, UI-wijziging, storage migratie, runtime market-data/FX fetch, suggesties/action drafts/orders en fake kostbasis/P-L/FX waarden.

## Task 125K — pure Decimal-only conversion-total calculator (no wiring)
- Status: afgerond.
- Toegevoegd: pure calculator module `packages/portfolio/src/portfolio_outlook_portfolio/valuation_conversion_totals.py` met deterministische statusuitkomsten en Decimal-only berekening op caller-provided opgeslagen inputs.
- Toegevoegd: unit tests `packages/portfolio/tests/test_valuation_conversion_totals.py` voor complete single/multi-currency, ontbrekende base/FX, stale/invalid/unknown FX, ontbrekende market/cash, geen inverse pair synthese en Decimal exactness.
- Niet toegevoegd: API wiring, endpoint contractwijziging, storage migratie, runtime FX/provider fetch, market-data runtime, suggesties/action drafts/orders en fake FX-rates/converted totals.

## Task 125J — Valuation conversion-total preflight (document-first, read-only)
- Nieuw document toegevoegd: `docs/product/valuation-conversion-total-preflight-task-125j.md`.
- Definieert purpose/boundary, required stored inputs, base-currency rules, FX pair rules, calculation boundaries, Decimal/rounding-regels, candidate readiness/status-contract en audittrace-eisen.
- Bevestigt expliciete non-goals: geen converted-total runtime, geen API calculation implementation, geen storage migration, geen runtime FX/provider fetch, geen market-data runtime, geen suggesties/action drafts/orders en geen fake FX-rates/converted totals/brokerdata.
- Aanbevolen volgende smalle implementatieslice: Task 125K (pure Decimal-only conversion calculator module + unit tests, zonder API wiring en zonder runtime fetch).

## Task 125H — FX snapshot storage schema/repository contract (read-only)

- Status: afgerond.
- Toegevoegd: duurzame `fx_rate_snapshots` opslagtabel + migratie + storage repositorycontract/methodes + Decimal round-trip tests.
- Grenzen bewaakt: geen runtime FX/provider fetch, geen market-data runtime, geen valuation conversion runtime, geen suggesties/action drafts/orders, geen fake FX-rates/converted totals.

- Task 125F — read-only FX snapshot-contract inventaris + valuation readiness contractstatus toegevoegd; geen runtime fetch, geen fake FX/totals.
- Task 125E — read-only valuation readiness verrijkt met cash/FX readiness (duurzame snapshots, geen runtime fetch, geen fake waarden).
## Task 127R2 — Final cleanup account-mode wording contradictions
- Status: Completed (documentation-only).
- Resterende bron-of-truth woordingscontradicties rond paper-only identiteit en real-money framing verwijderd.
- Formuleringen geharmoniseerd naar account-mode-aware + expliciete user-approved brokeractie veiligheidsgrenzen.
- Geen runtime code, tests, migraties, workflows of UI aangepast.


## Task 127 — account-mode-aware product direction + action-draft/Prediction Diary decision locks
- Status: afgerond (documentation-only).
- Nieuw document: `docs/product/action-draft-prediction-diary-alerts-decision-locks-task-127.md` als compacte source-of-truth voor 30 beslissingen.
- Productdocs geharmoniseerd: account-mode-aware identiteit (paper/real-money zichtbaar), IBKR operationele waarheid, user-approved acties, Prediction Diary/alerts/daily briefing in Version 1 scope.
- Geen runtime code, tests, migrations, workflows, package metadata of UI-code gewijzigd.

## Task 126 — Asset suggestion and financial algorithm roadmap (documentation/research only)

- Status: afgerond.
- Nieuw document toegevoegd: `docs/product/asset-suggestion-algorithm-roadmap.md`.
- Roadmap dekt berekeningen, risk metrics, factor/technical/fundamental lagen, probabilistische forecasting, gate-model, Decision Package-dependency, AI-rolgrenzen, validatie/model-risk en gefaseerde implementatie.
- Product conflict expliciet vastgelegd: eindrichting kan breder zijn dan paper-only, maar huidige Version-1 lock blijft paper-only; wijziging vereist aparte expliciete productbeslissingstaak.
- Geen runtime code, tests, migrations, workflows, package metadata of UI code gewijzigd.

## Task 125C-B-R
- Circular import reparatie afgerond door gedeelde IBKR sync dataclasses/protocol naar `ibkr_sync_contracts.py` te verplaatsen.

## Task 125C-B — Durable IBKR read-only sync runtime wiring
- Handmatige `/ibkr/sync/run` schrijft naast geheugenopslag nu ook naar duurzame opslag wanneer storage enabled/geconfigureerd/writable/migration-ready is via Task 125C-A persistence façade.
- Read-endpoints (`/ibkr/sync/status`, positions/cash/open-orders/executions) lezen duurzame latest-run snapshots wanneer beschikbaar en vallen anders terug op in-memory gedrag.
- Geen echte IBKR-netwerkadapter, geen TWS/IB Gateway connectie, geen order submit/modify/cancel/bind, geen scheduler/background sync, geen suggesties, geen Decision Packages, geen AI runtime, geen forecasting en geen fake data toegevoegd.

## Task 125A-R — Repair IBKR sync storage migration readiness
- Herstelde foutieve dubbele migratierevisie door `0023_ibkr_sync_snapshot_storage` te verplaatsen naar `0025_ibkr_sync_snapshot_storage` met `down_revision=0024_market_data_latest_snapshots`.
- Herstelde storage-readiness contracten (inventory/latest revision/count) en bijbehorende storage/API tests.
- Breidde de migratie uit zodat alle vijf IBKR snapshot-tabellen uit metadata worden aangemaakt en in veilige volgorde weer verwijderd.
- Geen API runtime wiring toegevoegd; geen IBKR netwerkcode; geen orders; geen scheduler; geen fake data.

- Task 122: **completed** — IBKR TWS/Gateway technical preflight documentatie toegevoegd en read-only IBKR sessiestatuscontract uitgebreid (disabled-by-default, geen auto-connect, geen orders, safety booleans false).

- Task 120: **completed** — disabled-by-default IBKR paper marktdata-adapter skeleton en handmatige latest-snapshot fetch route toegevoegd (status-first, read-only, geen scheduler/background fetch, geen fake data, safety booleans false).

- Task 117: market-data foundation slice gestart met typed provider boundary en identity-blocking contracttests.
- Task 112: **completed** — read-only request-audit detail drilldown pages toegevoegd voor request logs, provider/sources en freshness-audits, inclusief cross-links tussen request logs en freshness-audits waar linked IDs bestaan, plus web API client detail-contract hardening. Scope bleef non-runtime: geen provider calls, geen market-data runtime, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical fetching, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen IBKR connectie/orders en geen fake data. Task 107 tracking-drift preventieregel gevolgd; CI-check uitgevoerd vóór implementatie.

- Task 111: **completed** — conservatieve read-only audit viewer/API visibility foundation toegevoegd voor request logs, provider/source metadata en freshness-audit records in web UI. Geen provider calls, geen market-data runtime, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical fetching, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen IBKR connectie/orders en geen fake data. Safety booleans blijven conservatief false/blocked.

## Task 110E update

- Task 110E voltooid: read-only/status API exposure toegevoegd voor `/audit/request-logs`, `/audit/provider-sources` en `/audit/freshness-audits` (incl. detail endpoints), met API tests en producttracking bijgewerkt; non-runtime grenzen en conservatieve safety booleans (`false`) behouden.

# Task History (concise)

## Task 125R-R — API mypy Optional Decimal narrowing repair

- Status: afgerond.
- Gerichte reparatie op Task 125R-wiring: Optional Decimal narrowing in API mypy context hersteld voor valuation readiness.
- Niet gewijzigd: runtime market-data/latest-price fetch, runtime FX/provider fetch, suggesties, Decision Packages runtime, action drafts, orders, broker execution, storage/migraties en fake kostbasis/P/L/markt/FX/converted-total data.

## Task 125R — Wire cost-basis/unrealized P/L calculator into valuation readiness

- Status: afgerond.
- Task 125Q pure Decimal-only calculator read-only aangesloten op `GET /portfolio/valuation/readiness` met uitsluitend opgeslagen inputs en strikte safety-gates.
- Niet gewijzigd: runtime market-data/latest-price fetch, runtime FX/provider fetch, suggesties, Decision Packages runtime, action drafts, orders, broker execution, storage/migraties en fake kostbasis/P/L/markt/FX/converted-total data.

## Task 125G — FX snapshot storage contract preflight (document-first, read-only)

- Status: afgerond.
- Nieuw document toegevoegd: `docs/product/fx-snapshot-storage-contract-preflight-task-125g.md`.
- Definieert op designniveau het minimale toekomstige duurzame FX snapshot storagecontract + repositorycontract + valuation readiness API-read contract.
- Legt pair-derivation, freshness/validation statussemantiek, Decimal-safe regels en expliciete non-goals vast.
- Geen migraties, geen runtime FX/provider fetch, geen market-data runtime, geen suggesties, geen action drafts, geen orders/execution en geen fake FX-rates/converted totals toegevoegd.

## Task 127R — documentation-only repair
- Status: afgerond.
- Task 127 documentatiedrift hersteld in bron-of-truth docs.
- Stale paper-only productidentiteit-contradicties verwijderd en account-mode-aware richting vergrendeld.
- Task 127 decision-lock document uitgebreid met volledige detailbesluiten.
- Geen runtime wijzigingen, geen trading/execution gedrag, geen suggestieruntime, geen action-draftruntime, geen market-dataruntime.


## Task 109 — request-log/provider/source/freshness contract preflight (documentation/design only)

- Status: afgerond.
- Nieuw preflightdocument toegevoegd: `docs/product/request-log-provider-freshness-contract-preflight-task-109.md`.
- Candidate contractcatalogi vastgelegd voor request logs, provider/source metadata en freshness-audit records inclusief status-/reason-code proposals, traceability-linking en relatie naar bestaande read-only readiness contracten.
- Task 107 tracking-drift preventieregel nageleefd in dezelfde PR (current-state titel + `Huidige toestand:` + completionregel + task-history + scope-register + backlog + next-task geüpdatet).
- Geen storagetabellen, migrations, endpoints, schedulers, runtime-fetching, latest-price fetching, forecast runtime, AI runtime, suggesties, Decision Packages runtime, actiedrafts, orders of fake data toegevoegd.

## Task 108 — non-runtime foundation preflight (documentation/design only)

- Status: afgerond.
- Nieuw preflightdocument toegevoegd: `docs/product/non-runtime-foundation-preflight-task-108.md` met brede kandidatenreview en matrix.
- Exact één conservatieve volgende stap geselecteerd: Task 109 request-log/provider-metadata/freshness-audit storage/API contract preflight (zonder runtime).
- Task 107 tracking-drift preventieregel expliciet nageleefd in dezelfde PR (current-state, task-history, scope-register, backlog, next-task).
- Geen runtime market-data fetching, runtime-fetch, latest-price fetching, scheduler/background jobs, historical fetching, forecast runtime, AI runtime, suggesties, Decision Packages runtime, actiedrafts, orders of fake data toegevoegd.

## Task 107 — Read-only terminology sustainability tracking guardrail

- Status: afgerond (documentation/review-hardening only).
- Post-Task-106 producttrackingdocs gecontroleerd tegen de vergrendelde read-only terminology in `docs/product/locked-decisions.md`.
- Bekende drift hersteld in `docs/product/current-state.md` (titel + `Huidige toestand:` naar post-Task-106).
- Compacte sustainability-checknotitie toegevoegd: `docs/product/read-only-readiness-sustainability-check-task-107.md`.
- Compacte tracking-drift preventieregel toegevoegd in `docs/product/project-handover.md` en `docs/product/codex-ci-quality-rules.md` (documentation/review discipline, geen CI-automatisering).
- Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.

## Task 106 — Conservatieve read-only terminology lock discipline follow-up

- Status: afgerond (documentation/review-hardening only).
- Post-Task-105 producttrackingdocs gericht gecontroleerd tegen de vergrendelde read-only terminology in `docs/product/locked-decisions.md`.
- Kleine tracking/wordingdrift hersteld in `docs/product/current-state.md` (titel + samenvattingsregel naar post-Task-105 status).
- Compacte checknotitie toegevoegd: `docs/product/read-only-readiness-terminology-discipline-check-task-106.md`.
- Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.

## Task 105 — Conservatieve read-only terminology lock check follow-up

- Status: afgerond (documentation/review-hardening only).
- Post-Task-104 producttrackingdocs gecontroleerd tegen de vergrendelde read-only terminology in `docs/product/locked-decisions.md`.
- Kleine tracking/wordingdrift hersteld in `docs/product/current-state.md` (titel + samenvattingsregel naar post-Task-104 status) en compacte notitie toegevoegd: `docs/product/read-only-readiness-terminology-lock-check-task-105.md`.
- Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.

## Task 104 — Conservatieve read-only tracking consistency mini-follow-up

- Status: afgerond (documentation/review-hardening only).
- Post-Task-103 producttrackingdocs gecontroleerd tegen vergrendelde read-only terminology in `docs/product/locked-decisions.md`.
- Kleine trackingdrift hersteld in `docs/product/current-state.md` (na Task 103) en compacte notitie toegevoegd: `docs/product/read-only-readiness-tracking-consistency-task-104.md`.
- Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.

## Task 103 — Conservatieve read-only product-doc consistency follow-up

- Status: afgerond (documentation/review-hardening only).
- Post-Task-102 productupdates gericht gecontroleerd tegen de vergrendelde read-only terminology in `docs/product/locked-decisions.md`.
- Kleine tracking/wordingdrift hersteld in producttrackingdocs (o.a. current-state na-Task-102 status en conservatieve vervolgstap).
- Compacte notitie toegevoegd: `docs/product/read-only-readiness-consistency-check-task-103.md`.
- Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.

## Task 99 — Read-only readiness PR checklist en term-review rubric

- Status: afgerond (documentatie/review-guardrail-only).
- Nieuw document toegevoegd: `docs/product/read-only-readiness-pr-checklist.md` met purpose, toepassingsscope, verplichte reviewerchecklist, term-review rubric, PR-body standaardtekst en escalatieregel.
- Inventory-document gekoppeld als referentiebron + checklist als compacte PR-reviewtool.
- CI quality rules-document aangevuld met expliciete documentatie/review-guardrail voor UI/API wording- en contractwijzigingen (niet geautomatiseerd in CI).
- PR-template check uitgevoerd: geen bestaande PR-template gevonden onder `.github/`, dus geen templatewijziging gedaan.
- Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages/action drafts/orders en geen fake data toegevoegd.

## Task 98 — Read-only readiness UI/API contract inventory for remaining screens

- Status: afgerond (documentatie/inventaris-only).
- Nieuw document toegevoegd: `docs/product/read-only-readiness-ui-contract-inventory.md`.
- Inventaris dekt resterende UI-schermen + API/client readiness-contracten en legt vast:
  - veilige read-only labelpatronen;
  - onveilige termen die alleen met expliciete negatie mogen voorkomen;
  - conservative follow-up kandidaten zonder runtime-uitbreiding.
- Productdocs bijgewerkt voor traceability (current-state/backlog/scope-register/next-task).
- Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages/action drafts/orders en geen fake data toegevoegd.

## Task 96 — Conservatieve market-data readiness/latest-snapshot/watchlist terminologieharmonisatie

- Status: afgerond (read-only API/tests/docs scope).
- Watchlist `asset_listing_readiness`, market-data readiness `asset_listing_gate` en latest-snapshot responses gebruiken nu geharmoniseerde NL boundary-terminologie: read-only status, geen market-data runtime, geen runtime-fetch, geen analysevrijgave, geen suggesties, geen Decision Packages, geen actiedrafts en geen orders.
- Latest snapshot blijft read-only metadata/status-only en impliceert geen live/current marktprijs of runtime-fetch.
- Missing/unvalidated AssetListing blijft blocked; validated AssetListing blijft identity/status-only.
- Geen storage migration of nieuwe tabel.
- Geen market-data runtime/fetching/historical fetching/scheduler/forecast runtime/AI runtime/suggesties/Decision Packages/action drafts/IBKR-ordergedrag toegevoegd.
- Geen fake market prices, fake broker data of fake recommendations toegevoegd.

## Task 95 — Conservatieve market-data readiness AssetListing validation-gate harmonisatie

- Status: afgerond (read-only API/tests/docs scope).
- Market-data readiness list/detail responses bevatten nu een expliciete typed `asset_listing_gate` met statussen: `storage_unavailable`, `missing_ibkr_conid`, `missing_listing`, `unvalidated_listing`, `validated_listing`.
- Nederlandse status/helptekst geharmoniseerd met duidelijke read-only boundary: geen market-data runtime, geen analyse, geen suggesties, geen Decision Packages, geen actiedrafts, geen orders.
- Missing/unvalidated AssetListing blijft gate die market data/analysis/suggesties/action drafts blokkeert.
- Validated AssetListing blijft identity/listing gate-status en start geen runtime-fetching.
- Geen storage migratie, geen nieuwe tabel, geen market-data runtime/fetching/historical/scheduler, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages/action drafts/IBKR-ordergedrag, geen fake data.

## Task 94 — Conservatieve AssetListing-to-watchlist readiness wiring
- Status: completed
- Scope: API + tests + docs (read-only readiness contract wiring)
- Resultaat: watchlist list/detail response bevat typed AssetListing readiness/status gekoppeld via `ibkr_conid`; ontbrekende of ongevalideerde AssetListing houdt market data/analysis/suggesties/action drafts geblokkeerd; gevalideerde AssetListing toont alleen identity/status en activeert geen runtime.
- Niet toegevoegd: geen market-data runtime/fetching/historical/scheduler, geen forecast/AI runtime, geen suggesties/Decision Packages/action drafts/orders, geen fake prijzen/broker/recommendaties.

# Task History (concise)

## Task 127R — documentation-only repair
- Status: afgerond.
- Task 127 documentatiedrift hersteld in bron-of-truth docs.
- Stale paper-only productidentiteit-contradicties verwijderd en account-mode-aware richting vergrendeld.
- Task 127 decision-lock document uitgebreid met volledige detailbesluiten.
- Geen runtime wijzigingen, geen trading/execution gedrag, geen suggestieruntime, geen action-draftruntime, geen market-dataruntime.


## Task 106 — Conservatieve read-only terminology lock discipline follow-up

- Status: afgerond (documentation/review-hardening only).
- Post-Task-105 producttrackingdocs gericht gecontroleerd tegen de vergrendelde read-only terminology in `docs/product/locked-decisions.md`.
- Kleine tracking/wordingdrift hersteld in `docs/product/current-state.md` (titel + samenvattingsregel naar post-Task-105 status).
- Compacte checknotitie toegevoegd: `docs/product/read-only-readiness-terminology-discipline-check-task-106.md`.
- Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.

## Task 100 — Product-doc read-only readiness terminologie-audit

- Status: afgerond (documentatie/audit/harmonisatie-only).
- Nieuw document toegevoegd: `docs/product/read-only-readiness-product-doc-terminology-audit.md`.
- Scope: beperkte terminologie-audit op productdocs buiten de UI/API inventory, met `docs/product/read-only-readiness-ui-contract-inventory.md` als referentiebron.
- Focus: wording die ten onrechte runtime-readiness zou impliceren (live/current/latest prijs, market-data runtime/fetch, analysevrijgave, suggesties, Decision Packages runtime, actiedrafts, orders, AI-advies of fake data-acceptatie).
- Harmonisatie uitgevoerd op stale trackingverwijzingen waar nodig (o.a. current-state/scope/backlog/next-task verwijzingen).
- Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages/action drafts/orders en geen fake data toegevoegd.

## Task 92B — API pytest repair after Task 92 readiness hardening

- Status: completed.
- Scope: focused API/test/docs repair only.
- Root causes opgelost: (1) drift in gecentraliseerde readiness audit/help-tekst, en (2) snapshot metadata-validatie via `record.__dict__` die faalde voor attribute-based test doubles.
- Herstel: stabiele audit boundarytekst bevat nu expliciet `read-only` en `geen market-data runtime`; snapshot metadata wordt via attribute-based validatie opgebouwd voor zowel normale storage records als test doubles.
- API-gedrag blijft read-only; geen market-data runtime, historical fetching, scheduler/background job of AI runtime toegevoegd.
- Geen suggesties, Decision Packages, action drafts of IBKR-ordergedrag toegevoegd.
- Geen fake market prices, brokerdata of recommendations toegevoegd.
- Unresolved/unvalidated identiteiten blijven blocked voor market data, analyse, suggesties en action drafts.

## Task 92 — Conservative market-data readiness explainability and boundary consistency hardening

Resultaat: afgerond (read-only API-contract/test/docs).

Wat is opgeleverd:
- Deterministische blocked/ready/snapshot-semantiek voor market-data readiness verder gehard in list/detail contracts.
- Stabiele Nederlandse status/helpteksten gecentraliseerd voor readiness en latest-snapshot varianten.
- Expliciete non-implication boundaryvelden toegevoegd en vastgezet op `false`: `analysis_ready`, `suggestions_allowed`, `action_drafts_allowed`.
- Regressietests uitgebreid voor blocked identity, identity-ready zonder snapshot, snapshot metadata beschikbaar, detail endpoint en latest-snapshot varianten (`not_configured`, `missing_snapshot`, `snapshot_available`, `storage_failure`).
- Extra regressies bewijzen dat responses read-only status/auditmetadata blijven en geen analyse/suggesties/Decision Packages/action drafts/orders of fake prijs/recommendation-data impliceren.

Niet gedaan (bewuste scopegrens):
- Geen market-data runtime fetching.
- Geen historical fetching.
- Geen scheduler/background jobs.
- Geen AI runtime.
- Geen suggesties, Decision Packages, action drafts of IBKR-order behavior.
- Geen fake market prices, broker data of recommendations.

## Task 91 — Conservative market-data readiness status enum normalization and regression hardening

- Status: completed.
- Scope: API-contract + tests + docs hardening only (read-only).
- Readiness list/detail responses gebruiken nu expliciete typed statusnormalisatie voor readiness/freshness/blocker-codes.
- Nederlandse help/statusvelden zijn centraal gestabiliseerd en regressie-getest.
- Latest snapshot statusvarianten blijven genormaliseerd en regressie-getest: `not_configured`, `missing_snapshot`, `snapshot_available`, `storage_failure`.
- Geen market-data runtime toegevoegd.
- Geen historical fetching toegevoegd.
- Geen scheduler toegevoegd.
- Geen AI runtime toegevoegd.
- Geen suggesties, Decision Packages, action drafts of IBKR-ordergedrag toegevoegd.
- Geen fake market prices, brokerdata of recommendations toegevoegd.
- Unresolved/unvalidated identiteiten blijven blocked voor market data, analyse, suggesties en action drafts.

## Task 90 — Conservative market-data readiness API cleanup

- Status: completed.
- Scope: API-contract + tests hardening only (read-only).
- Endpoint `/market-data/snapshots/latest/{ibkr_conid}` gebruikt nu een expliciet typed responsecontract met vaste statusvarianten: `snapshot_available`, `missing_snapshot`, `not_configured`, `storage_failure`.
- Regressietests uitgebreid voor not-configured, missing-snapshot en storage-failure varianten + read-only metadata-only semantiek.
- Contract blijft expliciet blokkeren dat deze endpoint runtime-marktdata, analyse, suggesties, Decision Packages, action drafts of orders zou impliceren.
- Nederlandse status/help-tekst blijft eenvoudig en deterministisch.
- Geen market-data runtime toegevoegd.
- Geen historical fetching toegevoegd.
- Geen scheduler toegevoegd.
- Geen AI runtime toegevoegd.
- Geen suggesties, Decision Packages, action drafts of IBKR-ordergedrag toegevoegd.
- Geen fake market prices, brokerdata of recommendations toegevoegd.
- Unresolved/unvalidated identiteiten blijven blocked voor market data, analyse, suggesties en action drafts.

## Task 89 — Conservative API-readiness contract hardening

- Status: completed.
- Scope: API-contract + tests hardening only (read-only).
- Readiness/snapshot detailvarianten kregen expliciete typed coverage via dedicated snapshot-metadata responsemodel.
- Regressietests uitgebreid voor readiness list/detail response-contracten en conservatieve varianten (missing conid, unvalidated identity, missing snapshot, stored snapshot metadata).
- Nederlandse audit/status/help-velden blijven expliciet aanwezig en deterministisch.
- Geen market-data runtime toegevoegd.
- Geen historical fetching toegevoegd.
- Geen scheduler toegevoegd.
- Geen AI runtime toegevoegd.
- Geen suggesties, Decision Packages, action drafts of IBKR-ordergedrag toegevoegd.
- Geen fake market prices, brokerdata of recommendations toegevoegd.
- Unresolved/unvalidated identiteiten blijven blocked voor market data, analyse, suggesties en action drafts.

## Task 88L — CI restored after repository visibility change (documentation-only)

- Status: completed (documentation-only).
- Repository visibility changed from private to public; de eerdere GitHub Actions execution/logging blokkade is opgelost.
- CI run **#358** is groen met 6 geslaagde jobs: `domain`, `storage`, `portfolio`, `api`, `worker`, `web`.
- GitHub Actions logs en step-details zijn opnieuw zichtbaar.
- Geen code gewijzigd, geen tests gewijzigd, geen migraties gewijzigd, geen package metadata gewijzigd en geen workflows gewijzigd.

## Task 88I — Documentation-only roadmap update from Claude architecture audit

- Status: completed (documentation-only).
- Claude architecture/roadmap audit is reviewed; accepted bevindingen zijn vertaald naar backlog/locks/scope/next-task documentatie.
- Historische context ten tijde van Task 88I: toen was de GitHub Actions execution/logging blocker nog actief (later opgelost in Task 88L).
- Geen app-code, tests, migraties, package metadata of workflows aangepast.

## Task 88G — GitHub Actions platform-level failure diagnosis

- Status: completed (documentation-only).
- Na merge van PR #171 (`.github/workflows/ci-diagnostic.yml`) faalden 7 checks totaal: 6 normale CI jobs + 1 CI Diagnostic job.
- De minimale CI Diagnostic workflow faalde vóór bruikbare step logs en vóór artifact publicatie.
- Diagnose: geen geverifieerde repository/application-code root cause; blokkade zit waarschijnlijk op GitHub Actions platform/account/repository niveau (execution/logging/runner/quota/settings).
- Besluit: geen blind code-repair attempts uitvoeren zolang logging/executie niet hersteld is.
- Gate op dat moment: geen featurewerk en **Task 89 mocht niet starten** zolang CI rood bleef.
- Vervolgstatus: de tijdelijke diagnostische workflow is verwijderd nadat ze de blokkade bevestigde zonder bruikbare logs/artifacts; verwachte zichtbare failures na merge: terug naar 6 (alleen normale CI).


## Task 88 — Conservative readiness-contract consolidation

- Status: completed.
- API-only/read-only consolidatie uitgevoerd voor market-data readiness responses.
- Typed responsecontracten/helpers gecentraliseerd in API-module; route-opbouw met ad-hoc `dict[str, object]` verminderd.
- Regressietests bijgewerkt voor readiness list/detail shape en conservatieve NL audit/help velden.
- Geen market-data runtime, historical fetching, scheduler, AI runtime, suggesties, Decision Packages, action drafts of IBKR-ordergedrag toegevoegd.
- Geen fake market prices, brokerdata of aanbevelingen toegevoegd.
- Unresolved/unvalidated identiteiten blijven blocked voor market data, analyse, suggesties en action drafts.

## Task 88B — CI repair after Task 88

- Status: completed.
- Scope: uitsluitend CI/type/test/import-boundary repair; geen feature-uitbreiding.
- Root cause: readiness contract-module importeerde `WatchlistItem` uit `portfolio_outlook_api.watchlist`, waardoor een ongewenste dependency ontstond van een typed response/helper module naar route/store-georiënteerde API code.
- Fix: `build_readiness_row` accepteert nu een klein structureel typed protocol (`ReadinessWatchlistItemLike`) in `market_data_readiness.py`, zonder import van route-module modellen.
- Resultaat: typed readiness contracts blijven intact, routes blijven dun, en modulegrenzen zijn schoner/stabieler voor CI-controles.
- Geen market-data runtime, historical fetching, scheduler, AI runtime, suggesties, Decision Packages, action drafts of IBKR-ordergedrag toegevoegd.
- Geen fake market prices, brokerdata of aanbevelingen toegevoegd.
- Unresolved/unvalidated identiteiten blijven blocked voor market data, analyse, suggesties en action drafts.


## Tasks 65–67E

- **Task 65:** prompt-injection scan status foundation toegevoegd (storage/API), met conservatieve suggestieblokkade.
- **Task 66:** source credibility assessment status foundation toegevoegd (storage/API), met conservatieve suggestieblokkade.
- **Task 66B:** CI-reparatie na Task 66 (migratie/status testafstemming + formatting/testverwachtingen).
- **Task 67:** source evidence extraction foundation toegevoegd (storage/API) voor research-bronnen.
- **Task 67B:** API mypy repair voor storage public export van evidence record.
- **Task 67C:** extra mypy/public-export preventie + checklistversterking.
- **Task 67D:** API storage status pytest repair voor migratierevisie-afstemming.
- **Task 67E:** finale API pytest helper-type repair (`MigrationInventory` vs readiness report), CI terug groen.

## Lessons from Tasks 65–67 repairs

- Nieuwe migraties moeten **alle** migration inventory/status tests updaten.
- Nieuwe storage records moeten via package-root geëxporteerd worden bij cross-package imports.
- API `pytest` moet draaien als storage migration/status endpoint gedrag wijzigt.
- Helper returntypes eerst inspecteren vóór tests dynamisch gemaakt worden.
- Een PR is niet “ready” als exact falende package-checks niet lokaal zijn uitgevoerd.
- CI moet groen zijn vóór de volgende featuretaak start.

- **Task 68:** research-source evidence naar Evidence Ledger linking/lineage foundation toegevoegd (storage/API), audit-only en nog steeds geblokkeerd voor suggesties.
- **Task 69B:** repair na Task 69-merge met CI-fouten: storage `ruff`-fouten hersteld (importsortering + line wrapping), API `mypy` hersteld doordat `ResearchGateOutcomeRecord` niet via storage package-root geëxporteerd was, public-export smoke test uitgebreid, en preventieregels aangescherpt. Geen runtimegedrag gewijzigd; gate outcomes blijven audit/status-only en geblokkeerd voor suggesties; CI terug groen.

- **Task 69:** gate outcome records + freshness policy foundation toegevoegd als storage/API basis (audit/status-only), zonder suggestion/watchlist/IBKR/order runtimegedrag.


- **Task 70:** source conflict detection foundation toegevoegd (storage/API) voor audit/traceability; conflict records blijven suggestion-blocking en activeren geen watchlist/IBKR/ordergedrag.
- **Task 70B:** repair na Task 70-merge voor CI-fouten. Root causes: (1) API pytest faalde omdat conflict-finding test een niet-bestaande top-level `data` key verwachtte terwijl het endpoint het bestaande `record`-contract gebruikt; (2) storage pytest faalde omdat migration-readiness tests nog stale revision-assumpties (`14` en `0014`) hardcodeden na migratie `0017_research_source_conflict_findings`. Herstel: tests gealigneerd met bestaand API response-contract en migration inventory helper voor latest revision/count. Preventieregels in CI-quality-rules zijn verder aangescherpt. Geen runtimegedrag gewijzigd; conflict findings blijven audit/status-only en geblokkeerd voor suggesties.


## Task 70/70B/71/71B status lock

- **Task 70:** source conflict detection foundation toegevoegd (storage/API), audit/status-only.
- **Task 70B:** API response-shape test en stale migration-readiness tests gerepareerd.
- **CI-status na Task 70B:** groen op main.
- **Runtime-impact van Task 70B:** geen runtimegedrag gewijzigd.
- **Suggestion-status:** conflict findings blijven geblokkeerd voor suggesties.
- **Task 71:** asset master identity foundation toegevoegd (storage/API).
- **Task 71 impact:** asset identities blijven referentie/status-only; geen watchlist insertion, geen portfolio positions, geen suggestions, geen AI runtime, geen market-data runtime, geen forecast runtime, geen IBKR gedrag en geen ordergedrag.
- **Task 71B:** repair na Task 71-merge voor API mypy failure. Root cause: `asset_master.py` importeerde private helper `_get_repository` uit `research_sources.py`, waardoor mypy faalde met `attr-defined`.
- **Task 71B fix:** dependency boundary hersteld door repository-toegang lokaal en expliciet binnen `asset_master.py` af te handelen zonder private cross-route import.
- **Runtime-impact van Task 71B:** geen runtimegedrag gewijzigd.
- **CI-status na Task 71B:** groen op main.
- **Suggestion-status na Task 71/71B:** asset identity blijft referentie/status-only en geblokkeerd voor suggesties.

- **Task 72:** source-to-asset linking foundation toegevoegd (storage/API) met expliciete links van research/evidence/gate/conflict records naar canonieke asset-identiteiten; audit/reference/status-only en geblokkeerd voor suggesties.
- **Task 72B:** CI-repair na Task 72 afgerond: storage mypy row-to-record typing voor `SourceToAssetLinkRecord` hersteld en API pytest-fixture voor source-link endpoints gealigneerd met storage-config dependency, zonder runtimegedrag te wijzigen. Source-to-asset links blijven audit/reference/status-only; suggestions, watchlist insertion, portfolio positions, AI runtime, market-data runtime, forecast runtime, IBKR behavior en order behavior blijven afwezig.
- **Task 72C:** resterende API `pytest` failure na Task 72B gerepareerd. Root cause zat in de source-link endpoint test/fixture: de fake repository-instantie werd per request opnieuw opgebouwd, waardoor opgeslagen source-to-asset links niet zichtbaar waren bij de list-call binnen dezelfde testflow. Fix: test-fixture persistence gedeeld binnen dezelfde fake repository scope zodat create→list dezelfde in-memory linkset gebruikt. Geen runtimegedrag gewijzigd. Source-to-asset links blijven audit/reference/status-only; suggestions, watchlist insertion, portfolio positions, AI runtime, market-data runtime, forecast runtime, IBKR behavior en order behavior blijven afwezig.


## Task 73 — Docs: lock Release 1 functional workflow blueprint

- Status: completed (documentation-only).
- Nieuwe bron toegevoegd: `docs/product/release-1-functional-workflow-blueprint.md` als Release 1 functionele source-of-truth.
- Gerelateerde productdocs gesynchroniseerd (handover/final vision/locked decisions/backlog/scope/next task).
- Geen runtimecode gewijzigd.
- Geen migraties, API’s, UI, tests of tradinggedrag toegevoegd.
- Task 73 asset detection implementatie is niet gestart in deze taak.


## Task 74 — Modern GUI shell and dashboard foundation

- Status: completed.
- Moderne app shell toegevoegd met duidelijke navigatie en top-statusgebied.
- Dashboard foundation toegevoegd met metric cards, grafiek-placeholder, samenstelling/suggesties/briefingpanelen en sync-statuspaneel.
- Herbruikbare UI-componenten toegevoegd (status badges, panelen, empty states, tooltips, placeholders).
- Alle dashboardwaarden blijven eerlijk: geen fake cijfers, geen fake brokerdata, geen fake suggesties, geen fake chartdata.
- Geen runtime-engine toegevoegd voor IBKR, market data, suggestions, AI of orders.

## Task 75 — IBKR portfolio sync engine foundation

- Status: completed.
- Read-only IBKR sync foundation toegevoegd voor status, sync-run trigger, posities en cash snapshot API basis.
- Geen ordersubmission, geen action drafts, geen suggestions, geen Decision Packages en geen AI/market-data/forecast runtime toegevoegd.


## Task 76 — IBKR executions and open-orders sync foundation

- Status: completed.
- Task 75 read-only sync uitgebreid met open-orders snapshots en execution/fill snapshots.
- Read-only API endpoints toegevoegd voor `/ibkr/orders/open`, `/ibkr/executions` en uitgebreide `/ibkr/sync/status` tellers.
- Geen ordersubmission, orderwijziging of ordercancel toegevoegd.
- Geen action drafts, suggesties, Decision Packages, AI runtime, market-data runtime of forecast runtime toegevoegd.
- Tests blijven adapter-fake gebaseerd; geen echte IBKR connectie vereist.


## Task 76B / PR #153 — API mypy repair

- Status: completed.
- `ibkr_sync.py` run-count typing vernauwd naar `int` voor API mypy-compatibiliteit.
- CI terug groen na repair.
- Geen runtimegedrag gewijzigd; read-only IBKR snapshot scope bleef ongewijzigd.


## Task 77 — Portfolio read-only grid from IBKR snapshots

- Status: completed.
- Portefeuille-pagina toont nu read-only snapshots voor posities, cash, open orders en executions/fills via bestaande endpoints.
- Nederlandse helpertekst, statusbadge, last-sync en duidelijke empty/error/loading states toegevoegd.
- Geen orderknoppen, geen order submission/wijziging/cancel, geen action drafts, geen suggesties, geen Decision Packages, geen AI runtime, geen market-data runtime, geen forecast runtime.
- Geen fake broker/portfolio/order/execution data toegevoegd.

## Task 78B — Fix Task 78 CI failures

- Status: completed.
- Root causes: API `ruff` formatting violations in `apps/api/src/portfolio_outlook_api/watchlist.py` en `apps/api/tests/test_watchlist_endpoints.py`; storage tests hadden stale verwachtingen na migratie `0020_watchlist_foundation.py` en tabel `watchlist_items`.
- Fixes: importsortering/regelafbrekingen/semicolon cleanup in watchlist API code + testbestand; storage migration inventory test bijgewerkt naar 20 revisions inclusief `0020_watchlist_foundation.py`; metadata expected table set uitgebreid met `watchlist_items`.
- Verification: storage/api/web package-checks opnieuw gedraaid en groen.
- Runtime-impact: geen runtimegedrag gewijzigd, geen nieuwe features toegevoegd.
- Scope-lock blijft: watchlist blijft lokaal/manueel en gescheiden van IBKR-posities; geen suggesties, action drafts, IBKR-ordergedrag, AI runtime, market-data runtime, forecast runtime of fake data toegevoegd.


## Task 79 — Watchlist asset identity linking foundation
- Status: completed.
- Watchlist-item `asset_id` link/unlink flow uitgewerkt op API-niveau met validatie tegen bestaande Asset Master identiteit wanneer beschikbaar.
- Volglijst UI toont nu veilige linked/unlinked status + canonieke identiteitssamenvatting als die beschikbaar is.
- Scope guard: reference/status-only; geen suggesties, Decision Packages, action drafts, IBKR-ordergedrag, AI runtime, market-data runtime, forecast runtime of fake data.


## Task 80 — Asset Master search/picker UI foundation

- Read-only Asset Master zoekendpoint toegevoegd/hergebruikt voor veilige selectie van bestaande canonical identiteiten in de Volglijst-flow.
- Reusable picker-UI toegevoegd met Nederlandse zoek-, loading-, empty- en foutstatussen.
- Volglijst laat nu expliciet zoeken/selecteren/koppelen/ontkoppelen van bestaande Asset Master identiteiten toe zonder runtime-uitbreidingen buiten reference/status.
- Geen auto-creatie van Asset Master records.
- Geen portfoliopositiecreatie.
- Geen suggesties, Decision Packages, action drafts of IBKR-ordergedrag.
- Geen AI/market-data/forecast runtime en geen fake data.


## Task 81 — Docs: lock IBKR-contract-based watchlist, sync and freshness design

- Status: completed
- Type: documentation-only
- Locked dat actieve Volglijst-items IBKR-contract-based moeten zijn.
- Locked conid-based data-readiness rule: geen unresolved asset voor market data/analysis/suggestions/action drafts.
- Locked sync/freshness/performance roadmap-volgorde vóór market-data runtime.
- No runtime code changed.

- Task 82 — IBKR contract search and validation foundation: toegevoegd read-only adapter boundary + API endpoints voor contract search/details/validate met veilige not-configured status en genormaliseerde conid identity records. Geen market-data/historical/scheduler/suggestion/Decision Package/action draft/order/AI/forecast runtime.


- Task 83: Volglijst add-flow omgezet naar IBKR contractpicker; actieve creatie vereist gevalideerde IBKR-contractidentiteit. Bestaande losse records zonder contract blijven niet-gevalideerd en niet klaar voor analyse. Geen market-data runtime, historical fetching, schedulers, suggesties, Decision Packages, action drafts, IBKR-ordergedrag, AI runtime, forecast runtime of fake data toegevoegd.

- Task 84 afgerond: read-only IBKR-watchlist import foundation met conid-gebaseerde kandidaatimport en conflictmarkering; geen IBKR write-operaties.
- Task 84C: API pytest failures na PR #163 gerepareerd. Root causes: test setup gebruikte onterecht `dataclasses.replace()` op Pydantic `Settings`, en de configured-path test patchte IBKR settings niet waardoor endpoint terecht `not_configured` retourneerde. Herstel bleef test-only; geen runtime behavior toegevoegd en geen productscope uitgebreid (geen market-data runtime, historical fetching, schedulers, suggestions, Decision Packages, action drafts, IBKR order behavior, AI runtime, forecast runtime of fake data). Task 85 start niet vóór groene CI.


## Task 85 update

- Task 85 voltooid: conservatieve market-data storage/freshness foundation toegevoegd (schema + status-only API readiness endpoint).
- Geen market-data runtime toegevoegd, geen historical fetching, geen scheduler, geen AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag.
- Geen fake market prices of fake broker/recommendation data toegevoegd.
- Ongevalideerde of onopgeloste identiteiten blijven geblokkeerd voor market data en latere analyse/suggesties/actie-drafts.

- Task 86 afgerond: market-data readiness persistence wiring + read-only detail endpoints voor snapshotmetadata. Foundation-only; geen runtime fetch/scheduler/historical/AI/suggesties/orders.

- **Task 86B:** API CI-repair na Task 86. Root cause: `status_routes.py` gebruikte `payload = read_market_data_readiness()` gevolgd door iteratie over `payload["items"]`, waarbij mypy `dict[str, object]`-toegang als `object` typeerde. Fix: boundary cleanup door readiness-rows via een interne typed helper op te bouwen en direct te hergebruiken in detail endpoint. Geen runtimegedrag gewijzigd en geen scope-uitbreiding (geen market-data runtime/fetching, geen scheduler, geen AI/suggesties/Decision Packages/action drafts, geen IBKR-ordergedrag, geen fake data). CI moet groen blijven vóór de volgende featuretaak start.

- **Task 87:** conservatieve watchlist/readiness inspectieverbetering afgerond. Read-only readiness-responses geven nu expliciete Nederlandse audit/statusuitleg voor blocked en missing-snapshot paden (incl. `blocker_reason_nl`, `required_identity_fields`, `missing_identity_fields`, `validation_status`, `evaluated_at`, `next_step_nl`, `audit_help_nl`) en tonen snapshotmetadata alleen als read-only statusdetail. Geen market-data runtime, historical fetching, scheduler, AI runtime, suggesties, Decision Packages, action drafts of IBKR-ordergedrag toegevoegd; unresolved/unvalidated identities blijven geblokkeerd.

## Task 88J — Documentation-only Asset-Value Prediction Engine roadmap

- Status: completed (documentation-only).
- Nieuwe roadmapbron toegevoegd: `docs/product/asset-value-prediction-engine-roadmap.md` met volledige V1.0–V1.8 plan, model/AI/validatie/risk-gates/monitoring en Must-Should-Could scopeacceptatie.
- Geen runtimecode, tests, migraties, package metadata of GitHub workflows aangepast.
- CI-context ongewijzigd: bekende GitHub Actions blocker blijft; Task 89 blijft geblokkeerd.

## Task 93 — AssetListing identity foundation deepening
Status: completed. Scope: grotere maar begrensde foundationstap (storage/API/tests/docs), identity/reference/status-only.


## Task 101 — Anchor read-only readiness terminology in handover en locked decisions

Status: ✅ Completed (documentatie-only).

Resultaat:
- `project-handover.md` verwijst nu expliciet naar de read-only readiness terminologiedocs.
- `locked-decisions.md` bevat een compacte vergrendelde termenset voor pre-runtime wording.
- Lichte cross-links toegevoegd tussen inventaris, checklist, audit en locked decision.

Bevestiging scope:
- Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders, geen fake data.


## Task 102 — conservatieve read-only wording drift check (documentation-only)

- Status: afgerond.
- Productdocs gecontroleerd op post-Task-101 wording/tracking drift tegen de vergrendelde termenset in `docs/product/locked-decisions.md`.
- Gericht hersteld: current-state titel (“na Task 101”), backlog-plaatsing van Task 101 update en stale next-step wording.
- Driftchecknotitie toegevoegd: `docs/product/read-only-readiness-drift-check-task-102.md`.
- Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.


- Task 113 afgerond: read-only audit summary/count contracten + usability verbeteringen; geen runtime-unlock.


- Task 114 afgerond: read-only audit linked-record coverage/navigation hardening en web type-alignment; geen runtimegedrag toegevoegd.

## Task 123
- Read-only IBKR paper sync runtime foundation (account summary/cash/positions) toegevoegd achter handmatige trigger en disabled-by-default config.
- Geen ordersubmission/modificatie/cancel, geen suggesties, geen AI runtime, geen fake brokerdata.
## Task 125B completion update

- Task 125B is afgerond en gemerged via PR #258.
- Toegevoegd: repository dataclasses/records, SQL repositorygedrag (`save/get/list/latest`) voor de vijf duurzame IBKR snapshot-tabellen, publieke exports en storage-tests.
- Opslagcontract hardening bevestigd in tests: Decimal round-trip, `None`-preservatie en safety booleans blijven conservatief `false`.
- API/runtime wiring blijft bewust uitgesteld naar Task 125C.

## Task 125A update: durable IBKR snapshot storage foundation added; runtime wiring deferred to 125B.

## Task 125C-A — IBKR sync persistence mappers + façade scaffolding

- Status: afgerond als kleine veilige implementatieslice na eerdere brede Task 125C rollback.
- Toegevoegd: `apps/api/src/portfolio_outlook_api/ibkr_sync_persistence.py` met pure mappers (cash/position/open-order/execution/sync-run) en een minimale persistence-façade die Task 125B repository-methodes in vaste volgorde aanroept.
- Toegevoegd: gerichte API-tests in `apps/api/tests/test_ibkr_sync_persistence.py` voor Decimal/None-preservatie, conid-conversie, safety booleans false en call-order van de façade met fake repository.
- Niet gedaan in deze slice: geen endpoint runtime replacement, geen StorageConnectionProvider wiring vanuit sync endpoints, geen in-memory store vervanging, geen IBKR netwerkruntime, geen TWS/Gateway connectiecode, geen orders/suggesties/Decision Packages/AI runtime/forecasting/scheduler/market-data runtime/fake data.

- Task 125D: **completed** — read-only portfolio valuation voorbereiding toegevoegd vanuit duurzame IBKR sync snapshots, met expliciete blocked/control-needed status bij ontbrekende of verouderde marktdata. Geen market-data runtime, geen suggesties, geen action drafts, geen broker orders/execution en geen fake prijzen toegevoegd.

- Task 125I afgerond: valuation-readiness leest opgeslagen FX snapshotrecords read-only en rapporteert missing/stale/invalid expliciet zonder runtime fetch of unsafe totals.


- Task 125L afgerond: read-only wiring van Decimal-only conversion-total calculator in valuation readiness endpoint; alleen opgeslagen inputs, zonder runtime FX/provider fetch, zonder market-data runtime en zonder suggestions/action drafts/orders.
- Task 125N afgerond: read-only web/API-client display support toegevoegd voor valuation conversion totals met hergebruik van bestaande `GET /portfolio/valuation/readiness` contractvelden; typed web API-client contract voor dit endpoint toegevoegd; read-only dashboard display support toegevoegd; read-only Portefeuille-pagina valuation totals-sectie toegevoegd; alleen API-aangeleverde waarden en simpele Nederlandse labels gebruikt. Geen browser-side financiële berekeningen, geen API-behavior/model changes, geen runtime FX/provider fetch, geen market-data runtime, geen latest-price fetching, geen suggesties/action drafts/orders en geen fake FX-rates of fake converted totals.
- Task 125O afgerond (**completed**): read-only advanced valuation trace/details display toegevoegd op de Portefeuille-pagina met (her)gebruik van `ValuationTraceDetails`; bestaande `valuation_input_trace` en blocker fields hergebruikt uit bestaande `GET /portfolio/valuation/readiness` response; display-only met simpele Nederlandse labels. Geen browser-side financiële berekeningen, geen API-behavior/model changes, geen runtime FX/provider fetch, geen market-data runtime, geen latest-price fetching, geen suggesties/action drafts/orders en geen fake FX-rates of fake converted totals.
- Task 125O-R afgerond (**completed**): web build failure na Task 125O gerepareerd door `JSX.Element | null` te vervangen door `ReactElement | null` in `ValuationTraceDetails`; geen runtimegedrag gewijzigd, geen UI-logica gewijzigd; CI weer groen na repair.
- Task 125P afgerond (**completed**): document-first/read-only preflight toegevoegd voor cost-basis en unrealized P/L display rules (`docs/product/portfolio-valuation-cost-basis-pl-preflight-task-125p.md`) met opgeslagen IBKR snapshots en bestaande market/FX readiness gates als toekomstige inputs. Geen berekeningen toegevoegd, geen API-behavior changes, geen web UI-behavior changes, geen runtime FX/provider fetch, geen market-data runtime, geen latest-price fetching, geen suggesties/action drafts/orders en geen fake kostbasis, fake P/L, fake FX-rates of fake converted totals.
- Task 125M afgerond: document-first/read-only UI/API display contract preflight voor valuation conversion totals toegevoegd (`docs/product/valuation-conversion-total-display-contract-preflight-task-125m.md`); geen web UI behavior changes, geen API behavior changes, geen runtime FX/provider fetch, geen market-data runtime, geen suggesties/action drafts/orders en geen fake FX-rates/converted totals.

## Task 130P
- Status: completed.
- Resultaat: release-candidate-only manual testing policy vastgelegd; milestone batch planning guidance toegevoegd; kleine Task 131-route vervangen door Task 131B.
- Type: documentation/process-only.
- Runtime impact: geen runtimewijzigingen aan API/web/storage/sync/market-data/FX/suggesties/action drafts/Decision Packages/orders/broker execution; geen financiële berekeningen of fake data toegevoegd.

- Task 139 voltooid: read-only IBKR sync run history/diagnostics endpoints toegevoegd (`/ibkr/sync/runs`, `/ibkr/sync/runs/{sync_run_id}`) met status/counts/payload-validatie samenvatting en safetybooleans blijvend geblokkeerd. Geen TWS/Gateway runtime, geen session manager, geen schema/migraties.

## Task 145 — completed
- Milestone B runtime-boundary slice: dependency-free manual TWS/Gateway read-only status-check runtime boundary toegevoegd met injected fake clients in tests only. Runtime blijft disabled-by-default en paper-only enforced; geen real IBKR low-level client, geen ibapi/ib_insync, geen sockets by default, geen auto-connect/reconnect/persistente session manager, geen sync/market-data/FX runtime en geen suggesties/action drafts/orders/broker execution.

- Task 153-L — completed (documentation/product-lock recovery): consolidated owner-agreed Version 1 product experience locks in `docs/product/version-1-product-experience-locks.md`, repaired product-tracking drift after Task 152-R7, and set next task to Task 154.
