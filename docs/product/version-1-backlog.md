- Task 127: **completed** — documentation-only alignment voor account-mode-aware productrichting, action-draft/Prediction Diary/alerts/daily briefing decision locks. Geen runtimewijzigingen.
- Task 126 (documentation/research): afgerond — `docs/product/asset-suggestion-algorithm-roadmap.md` toegevoegd als beslis- en architectuurroadmap voor toekomstige suggestielaag; runtime blijft ongewijzigd.
- [x] Task 125C-B — Completed: wire IBKR read-only sync manual-trigger runtime to durable storage behind small persistence boundary with in-memory fallback; no orders/suggestions/fake data, no real IBKR network adapter or TWS/IB Gateway connection added.
- [x] Task 125C-A — Completed: small mapper + persistence façade scaffolding for durable IBKR sync storage bridge (API-side only); endpoint runtime behavior not replaced yet.
- [x] Task 125B — Completed in PR #258: IBKR sync storage repository dataclasses/records en SQL repository methods voor duurzame snapshot-tabellen toegevoegd (incl. public exports + storage tests); geen API/runtime wiring, geen orders, geen suggesties, geen fake data.

- Task 122: **completed** — IBKR TWS/Gateway technical preflight documentatie toegevoegd en read-only IBKR sessiestatuscontract uitgebreid (disabled-by-default, geen auto-connect, geen orders, safety booleans false).

- Task 120: **completed** — disabled-by-default IBKR paper marktdata-adapter skeleton en handmatige latest-snapshot fetch route toegevoegd (status-first, read-only, geen scheduler/background fetch, geen fake data, safety booleans false).

- Task 112: **completed** — read-only request-audit detail drilldown pages toegevoegd voor request logs, provider/sources en freshness-audits, inclusief cross-links tussen request logs en freshness-audits waar linked IDs bestaan, plus web API client detail-contract hardening. Scope bleef non-runtime: geen provider calls, geen market-data runtime, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical fetching, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen IBKR connectie/orders en geen fake data. Task 107 tracking-drift preventieregel gevolgd; CI-check uitgevoerd vóór implementatie.

- Task 111: **completed** — conservatieve read-only audit viewer/API visibility foundation toegevoegd voor request logs, provider/source metadata en freshness-audit records in web UI. Geen provider calls, geen market-data runtime, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical fetching, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen IBKR connectie/orders en geen fake data. Safety booleans blijven conservatief false/blocked.

## Task 110E update

- Task 110E voltooid: read-only/status API exposure toegevoegd voor `/audit/request-logs`, `/audit/provider-sources` en `/audit/freshness-audits` (incl. detail endpoints), met API tests en producttracking bijgewerkt; non-runtime grenzen en conservatieve safety booleans (`false`) behouden.

# Version 1 Backlog (operational source of truth)

Zie ook de einddoelarchitectuur in `docs/product/final-solution-vision.md`.

## A) Completed foundations


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
- toekomstige paper-only IBKR action grid
- user-confirmed paper submission (pas na alle gates)
- audit viewer
- AI event intelligence
- OpenAI usage/cost dashboard
- Belgian tax/compliance support
- deployment/backups/restore testing

## D) Future but not Version 1

- live trading
- real-money execution
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
- **IBKR Gateway skeleton (read-only/safe boundary) gepland**: centrale sessiestatus, auth/account-mode status, tickle/keepalive, request logging, pacing awareness, foutafhandeling, paper-only enforcement en latere order-serialisatiegrens.
- **Market-data readiness hardening vóór echte fetching**: request logs, provider/source metadata, snapshot timestamps, freshness policy, stale/null handling, geen zero-fill, geen stale last-known-price als verse data en geen analysis unlock op ontbrekende/stale data.
- **Usable-cash contract vóór action-drafts**: geen leveraged buying power als veilige cash; usable cash = beschikbare funds/cash minus pending buys, approved/submitted drafts en user buffer; alle cashcijfers moeten auditeerbaar zijn.
- **AI enforcement foundation vóór beslissingsinvloed**: AI-output moet schema-gevalideerd, evidence-linked en source-grounded zijn met injection/credibility/freshness/risk gates; AI mag geen financiële kerngetallen origineren.
- **Decision Package blijft harde voorwaarde vóór suggesties**: immutable/auditable package met identity, portfolio-state, market-data snapshot, evidence/sources, gate outcomes, model outputs, blockers en expiry/validity-window.
- **Eerste paper action flow blijft conservatief**: roadmap noteert LMT-only start; geen market orders, geen brackets/stops/trailing in eerste flow, DAY/GTC alleen als later expliciet ondersteund, user approval + backend safety recheck + IBKR confirmation handshake verplicht.
- **IBKR reply-handshake state machine vóór paper submission**: minimaal states Draft → Safety checked → User approved → Submitted → Awaiting IBKR reply → Reply confirmed → Working → Filled/Cancelled/Rejected → Reconciled.
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
- paper action workflow: future, LMT-only, user-approved, paper-only.

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
