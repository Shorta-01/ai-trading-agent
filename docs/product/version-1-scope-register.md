- Task 127: **completed** — documentation-only alignment voor account-mode-aware productrichting, action-draft/Prediction Diary/alerts/daily briefing decision locks. Geen runtimewijzigingen.
| Task 126 roadmap (documentation/research) | Completed | Nieuw roadmapdocument voor asset suggestion/algorithms/gates/AI-rolgrenzen en staged implementatie | Runtime ongewijzigd; Task 127/127R heeft de oude paper-only richting vervangen door account-mode-aware productrichting met zichtbare account mode en safety gates |
## Task 125J — valuation conversion-total preflight
- In scope: document-first/read-only preflight voor toekomstige converted valuation totals met Decimal-only criteria, required stored inputs, base-currency + FX-pair regels, calculation boundaries, candidate readiness/status-contract en teststrategie.
- Buiten scope: converted-total runtime, API calculation implementation, storage migrations, runtime FX/provider fetch, market-data runtime, scheduler/background jobs, suggesties/action drafts/orders/execution en fake FX-rates/converted totals/brokerdata.

## Task 125C-B scope update
- Binnen scope: API runtime wiring van bestaande handmatige IBKR read-only sync naar duurzame opslag met kleine persistence boundary en in-memory fallback.
- Buiten scope: echte IBKR netwerkadapter/TWS connectie, order submit/modify/cancel/bind, suggesties, Decision Packages, AI runtime, forecasting, scheduler/background sync, market-data runtime en fake data.

## Task 125A-R scope update
- Binnen scope: CI-repair en schema/migratie-consistentie voor read-only IBKR snapshotopslag.
- Buiten scope (blijft uitgesteld): API/runtime wiring voor IBKR sync persistence (Task 125C), orders, suggesties, AI, forecasting, background sync.

- Task 122: **completed** — IBKR TWS/Gateway technical preflight documentatie toegevoegd en read-only IBKR sessiestatuscontract uitgebreid (disabled-by-default, geen auto-connect, geen orders, safety booleans false).

- Task 120: **completed** — disabled-by-default IBKR paper marktdata-adapter skeleton en handmatige latest-snapshot fetch route toegevoegd (status-first, read-only, geen scheduler/background fetch, geen fake data, safety booleans false).

- Task 112: **completed** — read-only request-audit detail drilldown pages toegevoegd voor request logs, provider/sources en freshness-audits, inclusief cross-links tussen request logs en freshness-audits waar linked IDs bestaan, plus web API client detail-contract hardening. Scope bleef non-runtime: geen provider calls, geen market-data runtime, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical fetching, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen IBKR connectie/orders en geen fake data. Task 107 tracking-drift preventieregel gevolgd; CI-check uitgevoerd vóór implementatie.

- Task 111: **completed** — conservatieve read-only audit viewer/API visibility foundation toegevoegd voor request logs, provider/source metadata en freshness-audit records in web UI. Geen provider calls, geen market-data runtime, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical fetching, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen IBKR connectie/orders en geen fake data. Safety booleans blijven conservatief false/blocked.

## Task 110E update

- Task 110E voltooid: read-only/status API exposure toegevoegd voor `/audit/request-logs`, `/audit/provider-sources` en `/audit/freshness-audits` (incl. detail endpoints), met API tests en producttracking bijgewerkt; non-runtime grenzen en conservatieve safety booleans (`false`) behouden.

# Ai Trading Agent — Version 1 Scope Register

## Task 125G — FX snapshot storage contract preflight
- Status: afgerond (document-first/read-only).
- Nieuw preflightdocument: `docs/product/fx-snapshot-storage-contract-preflight-task-125g.md` met minimale toekomstige FX snapshot storage/repository/API-read contractdefinitie op designniveau.
- Geen runtime/code/tests/migrations/workflows/UI gewijzigd; geen runtime FX fetch, geen market-data runtime, geen suggesties, geen action drafts, geen orders/execution en geen fake FX-rates/converted totals.

Zie ook `docs/product/final-solution-vision.md` voor het einddoel.

## Task 125K — conversion-total calculator foundation
- Status: afgerond (pure calculatiemodule + tests).
- Toegevoegd: pure Decimal-only conversion-total calculator in `packages/portfolio` op opgeslagen inputs, met deterministische statusvelden en trace metadata passthrough.
- Geen API wiring, geen endpointgedragwijziging, geen storage migratie, geen runtime FX/provider fetch, geen market-data runtime, geen suggesties/action drafts/orders en geen fake FX-rates/converted totals.

## Status definitions

- Contracted
- Storage implemented
- API implemented
- UI implemented
- Runtime pending
- Blocked for suggestions

## Traceability (current implemented state)

| Capability | Domain | Storage | API | UI | Runtime status | Suggestion/IBKR/order status |
|---|---|---|---|---|---|---|
| Research source archive | Contracted | Storage implemented | API implemented | UI implemented | Runtime pending (gedeeltelijk) | Blocked for suggestions; geen IBKR/order gedrag |
| Safe file upload | Contracted | Storage implemented | API implemented | UI implemented | Foundation exists | Blocked for suggestions; geen IBKR/order gedrag |
| TXT/MD/CSV extraction | Contracted | Storage implemented | API implemented | UI implemented | Foundation exists | Blocked for suggestions; geen IBKR/order gedrag |
| Deterministic document classification | Contracted | Storage implemented | API implemented | UI implemented | Foundation exists | Blocked for suggestions; geen IBKR/order gedrag |
| Prompt-injection scan status | Contracted | Storage implemented | API implemented | UI implemented (status zichtbaar) | **Runtime engine pending** | Blocked for suggestions; geen IBKR/order gedrag |
| Source credibility status | Contracted | Storage implemented | API implemented | UI implemented (status zichtbaar) | **Runtime scoring engine pending** | Blocked for suggestions; geen IBKR/order gedrag |
| Source evidence items (Task 67) | Contracted | Storage implemented | API implemented | UI implemented (status/foundation) | **Evidence runtime verdieping pending** | Blocked for suggestions; geen IBKR/order gedrag |
| Evidence Ledger API/linking (Task 68) | Contracted | Storage implemented | API implemented | UI pending | Runtime pending | Blocked for suggestions; geen IBKR/order gedrag |
| Research Library source pipeline overall | Contracted | Storage/API/UI foundations implemented | API implemented | UI implemented | Full runtime pipeline pending | Blocked for suggestions; geen IBKR/order gedrag |
| Gate outcome/freshness foundation (Task 69) | Contracted | Storage implemented | API implemented | UI pending | Runtime pending | Blocked for suggestions; audit/status-only; geen watchlist/IBKR/order gedrag |
| Source conflict findings (Task 70) | Contracted | Storage implemented | API implemented | UI pending | Runtime pending (analysis engine pending; storage/API foundation implemented) | Blocked for suggestions; audit/status-only; geen AI/watchlist/IBKR/order gedrag |
| Asset master identity foundation (Task 71) | Contracted | Storage implemented | API implemented | UI pending | Runtime pending (advanced identity validation/mapping pending; foundation is reference/status-only) | Blocked for suggestions; geen watchlist/portfolio/IBKR/order gedrag; geen AI/market-data/forecast runtime |
| Source-to-asset linking foundation (Task 72) | Contracted | Storage implemented | API implemented | UI pending | Runtime pending (asset detection/matching runtime pending) | Blocked for suggestions; audit/reference-only; geen AI/watchlist/portfolio/IBKR/order gedrag |
| CI quality governance rules | Locked | N/A | N/A | N/A | Implemented as mandatory workflow docs | Geen safety gate verzwakking toegestaan |

| Task 109 request-log/provider/source/freshness contract preflight | Contracted | N/A | N/A | N/A | Runtime pending | Documentatie/design-only preflight met kandidaatveldencatalogi, status/reason-code voorstellen en traceability-linking (`docs/product/request-log-provider-freshness-contract-preflight-task-109.md`); geen storagetabellen/migrations/endpoints/schedulers/runtime-fetching/latest-price fetching/forecast runtime/AI runtime/suggesties/Decision Packages runtime/actiedrafts/orders/fake data. |

| Portfolio sync from IBKR | Core workflow | Storage implemented (repository-laag voor snapshots) | Planned | UI pending | Runtime pending (API/service wiring pending in Task 125C) | Geen runtime-implementatie; IBKR blijft operationele waarheid |
| Watchlist assets (manuele toevoeging, gescheiden van portfolio) | Core workflow | Planned | Planned | Planned | Runtime pending | Suggesties mogelijk na gates; geen automatische orders |
| Decision Package | Core workflow | Planned | Planned | Planned | Runtime pending | Kernobject voor auditbare suggesties; nog niet geïmplementeerd |
| Suggestions grid (Actief/Verlopen/Historiek) | Core workflow | Planned | Planned | Planned | Runtime pending | Portfolio/watchlist toont enkel laatste actieve hoofdsuggestie |
| IBKR Action Center (Te keuren/Actief bij IBKR/Historiek) | Core workflow | Planned | Planned | Planned | Runtime pending | Submission enkel na user approval; geen auto-trading |
| Prefilled action drafts | Core workflow | Planned | Planned | Planned | Runtime pending | Bewerkbaar vóór submit; audit op system-draft + user edits |
| Action safety checks | Core workflow | Planned | Planned | Planned | Runtime pending | Hard checks blokkeren uitvoering bij falen |
| Sync/recompute engine (jobs/events/manual refresh) | Core workflow | Planned | Planned | Planned | Runtime pending | Hybride refreshmodel; nog geen runtime |
| AI analytics layer | Core workflow | Planned | Planned | Planned | Runtime pending | Gestructureerde evidence-signalen; AI maakt geen orders |
| Daily briefing | Core workflow | Planned | Planned | Planned | Runtime pending | Dagelijkse wijzigingssamenvatting met evidence-links |
| Release 1 end-to-end acceptance workflow | Core workflow | Planned | Planned | Planned | Runtime pending | Niet compleet tot volledige keten werkt |

## Hard boundaries (Version 1)

- Geen live trading.
- Geen automatische brokeractie.
- Geen automatische orders.
- Geen IBKR live order flow.
- Suggesties blijven geblokkeerd tot alle gates/runtime engines bestaan.


| Moderne GUI shell + dashboard foundation (Task 74) | Contracted | N/A | N/A | UI implemented | Runtime pending | UI-only foundation; geen IBKR/market-data/suggestion/AI/order runtime; gebruikt veilige empty states zonder fake data |

| IBKR portfolio sync foundation (Task 75) | Contracted | Storage foundation aanwezig | API implemented | UI pending (status wiring minimaal) | Runtime pending (echte IBKR connectie) | Read-only; geen ordersubmission/suggestions/AI/market-data/forecast runtime |

| IBKR open-orders + executions snapshots foundation (Task 76) | Contracted | Storage foundation aanwezig (in-memory foundation) | API implemented | UI implemented (dashboard tellers minimaal) | Runtime pending (echte IBKR connectie) | Read-only; geen ordersubmission/wijziging/cancel, geen action drafts/suggesties/Decision Packages/AI/market-data/forecast runtime |

| Portefeuille read-only snapshot grid (Task 77) | Contracted | N/A | API hergebruikt (Task 75/76) | UI implemented | Runtime pending (echte IBKR connectie) | Read-only; toont opgeslagen snapshots voor posities/cash/open orders/executions; geen ordersubmission/-wijziging/-cancel, geen action drafts/suggesties/Decision Packages/AI/market-data/forecast runtime en geen fake data |

| Watchlist foundation + Volglijst page (Task 78, CI repaired in Task 78B) | Contracted | Storage implemented | API implemented | UI implemented | Runtime pending | Lokaal/manueel, gescheiden van IBKR-portfolio; geen suggesties/action drafts/IBKR-ordergedrag/AI/market-data/forecast runtime; geen fake data |

| Watchlist-to-Asset-Master identity linking foundation (Task 79) | Contracted | Bestaande storage hergebruikt (`watchlist_items.asset_id`) | API implemented | UI implemented (statusbadge + read-only canonical samenvatting) | Runtime pending | Reference/status-only; geen auto Asset Master create; geen portfolioposities/suggesties/Decision Packages/action drafts/IBKR-ordergedrag/AI/market-data/forecast runtime; geen fake data |

| Asset Master search/picker UI foundation (Task 80) | Contracted | Bestaande storage hergebruikt (Asset Master records read-only) | API implemented (`GET /assets/master/search`) | UI implemented (Volglijst picker component + koppelen/ontkoppelen) | Runtime pending | Reference/status-only; selecteert alleen bestaande asset-identiteiten; geen auto Asset Master create, geen portfolioposities/suggesties/Decision Packages/action drafts/IBKR-ordergedrag/AI/market-data/forecast runtime; geen fake data |


| IBKR contract identity validation | Core workflow | Planned | Planned | Planned | Runtime pending | Active watchlist requires validated IBKR identity before data/analysis runtime |
| IBKR conid mapping | Core workflow | Planned | Planned | Planned | Runtime pending | Conid mapping required for market data readiness; ticker text alone is insufficient |
| IBKR-contract-based Volglijst activation | Core workflow | Planned | Planned | Planned | Runtime pending | Only resolved IBKR contracts may become active watchlist items |
| System-detected asset candidate resolution | Core workflow | Planned | Planned | Planned | Runtime pending | Detected assets remain candidates until IBKR contract resolution succeeds |
| IBKR watchlist sync | Core workflow | Planned | Planned | Planned | Runtime pending | Import/export later; must stay conid-based with auditable conflicts |
| Data freshness and priority engine | Core workflow | Planned | Planned | Planned | Runtime pending | Hot/warm/cold freshness tiers and readiness states |
| Historical data backfill scheduler | Core workflow | Planned | Planned | Planned | Runtime pending | Pacing-aware backfill queue before serious analysis |
| Market snapshot scheduler | Core workflow | Planned | Planned | Planned | Runtime pending | Latest snapshot scheduler layered with freshness policy |
| Fast alert layer | Core workflow | Planned | Planned | Planned | Runtime pending | Early signal layer on validated identities only |
| AI event trigger layer | Core workflow | Planned | Planned | Planned | Runtime pending | Event-analysis trigger foundation on validated, freshness-aware data |

| IBKR contract search/validation foundation (Task 82) | Contracted | API foundation implemented | Read-only endpoints implemented | UI not converted yet | Runtime pending | Identity/reference-only; safe not-configured behavior; no market-data/historical/scheduler/suggestions/Decision Packages/action drafts/order/AI/forecast runtime |


- Task 83: Volglijst add-flow omgezet naar IBKR contractpicker; actieve creatie vereist gevalideerde IBKR-contractidentiteit. Bestaande losse records zonder contract blijven niet-gevalideerd en niet klaar voor analyse. Geen market-data runtime, historical fetching, schedulers, suggesties, Decision Packages, action drafts, IBKR-ordergedrag, AI runtime, forecast runtime of fake data toegevoegd.

- Task 84: IBKR-watchlist import foundation toegevoegd (identity/reference/sync-only, read-only richting IBKR).
- Task 84C: API pytest-repair na PR #163 afgerond als test-setup fix (Pydantic `Settings` correct gepatcht; configured-path test kreeg expliciete IBKR configuratiepatch). Geen runtime behavior toegevoegd, geen productscope uitgebreid en geen toevoeging van market-data runtime, historical fetching, schedulers, suggestions, Decision Packages, action drafts, IBKR order behavior, AI runtime, forecast runtime of fake data.


## Task 85 update

- Task 85 voltooid: conservatieve market-data storage/freshness foundation toegevoegd (schema + status-only API readiness endpoint).
- Geen market-data runtime toegevoegd, geen historical fetching, geen scheduler, geen AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag.
- Geen fake market prices of fake broker/recommendation data toegevoegd.
- Ongevalideerde of onopgeloste identiteiten blijven geblokkeerd voor market data en latere analyse/suggesties/actie-drafts.

| Market-data readiness persistence wiring (Task 86) | Contracted | Storage read-contracten geïmplementeerd | API read-only detail endpoints geïmplementeerd | UI pending | Runtime pending | Geen market-data runtime/historical/scheduler/AI/suggesties/orders; unresolved identities blijven blocked. |

| Task 86B API CI-repair (post-Task 86) | Contracted | N/A | API type-boundary repair uitgevoerd | UI N/A | Runtime onveranderd | Root cause: mypy iteratie op `dict[str, object]["items"]`; fix is type cleanup only. Geen market-data runtime/historical/scheduler/AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag/fake data; unresolved identities blijven blocked voor market data/analysis/suggesties/action drafts. |

| Task 87 readiness inspectieverbetering | Contracted | Bestaande storage-read contracten hergebruikt | API read-only readiness/auditvelden uitgebreid + tests bijgewerkt | UI optioneel/pending | Runtime onveranderd | Duidelijkere blocked/missing-snapshot uitleg in NL; geen market-data runtime/historical/scheduler/AI/suggesties/orders; unresolved identities blijven blocked. |

| Task 88 readiness-contract consolidatie | Contracted | Bestaande storage-read contracten hergebruikt | API implemented (typed readiness responsecontracten/helpers gecentraliseerd) | UI N/A | Runtime pending | Read-only consolidatie; geen market-data runtime/historical/scheduler/AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag; unresolved identities blijven blocked. |
| Task 88B CI-repair na Task 88 | Contracted | N/A | API import-boundary/type repair uitgevoerd (protocol-based input contract in readiness helper) | UI N/A | Runtime onveranderd | CI/type repair only; geen market-data runtime/historical/scheduler/AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag; geen fake data; unresolved identities blijven blocked. |
| Task 89 API-readiness contract hardening | Contracted | Bestaande storage-read contracten hergebruikt | API implemented (extra typed snapshot-detail coverage + regressietests) | UI N/A | Runtime pending | Read-only hardening only; geen market-data runtime/historical fetching/scheduler/AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag; unresolved/unvalidated identities blijven blocked. |
| Task 90 market-data readiness API cleanup | Contracted | Bestaande storage-read contracten hergebruikt | API implemented (snapshot-latest endpoint expliciet typed responsecontract + regressietests not-configured/missing-snapshot/storage-failure) | UI N/A | Runtime pending | Read-only API-contract/test hardening only; geen market-data runtime/historical fetching/scheduler/AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag; geen fake prices/broker/recommendations; unresolved/unvalidated identities blijven blocked. |
| Task 91 readiness status enum-normalisatie + regressiehardening | Contracted | Bestaande storage-read contracten hergebruikt | API implemented (list/detail readiness-statussen expliciet typed/genormaliseerd + regressietests voor stabiele NL help/statusvelden; latest-snapshot varianten blijven genormaliseerd/getest) | UI N/A | Runtime pending | Read-only API-contract/test/docs hardening only; geen market-data runtime/historical fetching/scheduler/AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag; geen fake prices/broker/recommendations; unresolved/unvalidated identities blijven blocked. |
| Task 92 readiness explainability + boundary-consistency hardening | Contracted | Bestaande storage-read contracten hergebruikt | API implemented (stabiele NL help/status uitleg gecentraliseerd; expliciete boundaryvelden `analysis_ready`/`suggestions_allowed`/`action_drafts_allowed` vast op false; deterministische list/detail/latest-snapshot semantiek regressie-getest) | UI N/A | Runtime pending | Read-only API-contract/test/docs hardening only; geen market-data runtime/historical fetching/scheduler/AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag; geen fake prices/broker/recommendations; unresolved/unvalidated identities blijven blocked. |

| Task 88G CI-diagnose lock | Completed (historical) | N/A | N/A | N/A | Historische diagnose van eerdere CI execution/logging blokkade buiten app-code | Vastgelegd als eerdere blokkade; opgelost in Task 88L na visibility change naar public. |
| Task 88L CI restoration record | Completed (documentation-only) | N/A | N/A | N/A | CI restored; run #358 passed | 6 normale jobs groen (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`); logs/steps weer zichtbaar; normale feature-gate blijft groene CI. |


## Planned capability additions from architecture audit (Task 88I)

| Planned capability | Status | Scope note |
|---|---|---|
| AssetListing identity model (naast AssetMaster) | Planned | Nodig vóór serieuze market-data/analyse/suggesties; conid op listing-niveau met identity-history. |
| Centrale IBKR Gateway skeleton (read-only/safe boundary) | Planned | Sessiebeheer, auth/account-mode status, keepalive, logging, pacing, account-mode visibility/verification enforcement. |
| Market-data pacing/freshness hardening | Planned | Geen fetch-unlock zonder freshness/quality gates; geen zero-fill of stale-hergebruik als fresh. |
| Deterministisch usable-cash contract | Planned | Buying power is geen veilige cash; cashberekening volledig auditeerbaar. |
| AI enforcement foundation | Planned | Schema-validatie + evidence-linking + safety gates vóór AI-impact op beslissingen. |
| Decision Package storage/API/UI | Planned | Verplicht vóór suggestions; immutable/auditable beslissingscontext. |
| Account-mode-aware action state machine + IBKR reply handshake | Planned | Verplicht vóór toekomstige account-mode-aware, user-approved broker action flow; account mode zichtbaar/geverifieerd vóór submit. |

## Prediction-engine capabilities register addendum (Task 88J)

| Capability | Status |
|---|---|
| Asset-Value Prediction Engine roadmap document | Contracted (documentation) |
| V1.0 foundations set | Planned / Runtime pending |
| V1.1 baseline forecasting stack | Planned / Runtime pending |
| V1.2 AI text-to-feature layer | Planned / Runtime pending |
| V1.3 challenger TSFM stack | Planned / Runtime pending |
| V1.4 Dutch explanation RAG layer | Planned / Runtime pending |
| V1.5 dissent challenger layer | Planned / Runtime pending |
| V1.6 monitoring/drift/calibration diary | Planned / Runtime pending |
| V1.7 immutable Decision Package + deterministic labels | Planned / **Blocked for suggestions until validated gates** |
| V1.8 account-mode-aware user-approved broker action workflow | Planned |

Extra lock: suggestions/action drafts blijven blocked tot data/model/evidence/freshness/risk gates + approved modelversion actief zijn.

- In scope afgerond: AssetListing identity foundation als aparte laag naast AssetMaster, inclusief listing-level IBKR conid representatie en blocked-by-default safetyvelden.


- Task 94 (completed): watchlist API exposeert nu read-only AssetListing readiness/status per `ibkr_conid`; unresolved/unvalidated listings blijven hard geblokkeerd voor market data/analysis/suggesties/action drafts; geen runtime market-data/forecast/AI/actions/orders toegevoegd.

- Task 95 (completed): market-data readiness list/detail bevat expliciete typed AssetListing validation-gate status in read-only contract; missing/unvalidated listing blijft blocked; validated listing blijft status-only zonder runtime-fetch. Geen runtime market-data/forecast/AI/suggesties/Decision Packages/action drafts/orders toegevoegd.

| Task 96 readiness/watchlist/latest-snapshot terminologieharmonisatie | Contracted | Bestaande storage-read contracten hergebruikt | API implemented (geharmoniseerde read-only NL boundary-terminologie + regressietests) | UI N/A | Runtime pending | Geen market-data runtime/fetching/historical/scheduler/forecast/AI/suggesties/Decision Packages/action drafts/orders; latest snapshot blijft metadata/status-only; missing/unvalidated listings blijven blocked. |


| Task 98 read-only readiness UI/API contract inventory | Contracted | N/A | N/A | N/A | Runtime pending | Documentatie/inventaris-only guardrail voor labelconsistentie in resterende schermen + readiness-contracten; geen runtime market-data/latest-price fetching/scheduler/forecast/AI/suggesties/Decision Packages/action drafts/orders/fake data. |


## Task 99 (documentation/review-guardrail only)

Task 99 voegt een compacte read-only readiness PR-checklist en term-review rubric toe als documentatie/review-guardrail. Dit verandert geen runtimegedrag en unlockt geen market-data runtime, latest-price fetching, scheduler/background jobs, forecast runtime, AI runtime, suggesties, Decision Packages, action drafts of orders.

## Task 100 (documentation/audit/harmonization only)

Task 100 voegt een beperkte product-doc terminologie-audit toe voor read-only readiness buiten de UI/API inventory, inclusief het nieuwe document `docs/product/read-only-readiness-product-doc-terminology-audit.md`.
Stale trackingverwijzingen zijn conservatief geharmoniseerd waar nodig; geen runtimegedrag gewijzigd en geen market-data runtime, runtime-fetch/latest-price fetching, scheduler/background jobs, forecast runtime, AI runtime, suggesties, Decision Packages runtime, actiedrafts, orders of fake data toegevoegd.


## Task 101 update (documentation-only)

Task 101 heeft de Task 100 read-only readiness termenset verankerd op product-koppelpunten (handover, locked decision, cross-links). Dit is een review-/terminologieguardrail en geen runtimefeature. Geen market-data/latest-price runtime-fetching, geen scheduler/background jobs, geen forecast/AI runtime, geen suggesties/Decision Packages/actiedrafts/orders, geen fake data.


## Task 102 — conservatieve read-only wording drift check (documentation-only)

- Status: afgerond.
- Productdocs gecontroleerd op post-Task-101 wording/tracking drift tegen de vergrendelde termenset in `docs/product/locked-decisions.md`.
- Gericht hersteld: current-state titel (“na Task 101”), backlog-plaatsing van Task 101 update en stale next-step wording.
- Driftchecknotitie toegevoegd: `docs/product/read-only-readiness-drift-check-task-102.md`.
- Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.


## Task 104 tracking consistency mini-follow-up (documentation/review-hardening only)

- Status: afgerond.
- Post-Task-103 producttracking gecontroleerd tegen vergrendelde read-only terminology in `docs/product/locked-decisions.md`.
- Kleine trackingdrift hersteld in `current-state.md` (na Task 103) en compacte notitie toegevoegd: `docs/product/read-only-readiness-tracking-consistency-task-104.md`.
- Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.



## Task 106 terminology lock discipline follow-up (documentation/review-hardening only)

- Status: afgerond.
- Post-Task-105 producttrackingdocs gecontroleerd tegen de vergrendelde read-only terminology in `docs/product/locked-decisions.md`.
- Kleine tracking/wordingdrift hersteld in `docs/product/current-state.md` (titel + samenvattingsregel nu post-Task-105).
- Compacte notitie toegevoegd: `docs/product/read-only-readiness-terminology-discipline-check-task-106.md`.
- Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.

## Task 105 terminology lock check follow-up (documentation/review-hardening only)

- Status: afgerond (productdocumentatie-only).
- Post-Task-104 trackingdocs gericht gecontroleerd tegen de vergrendelde read-only terminology in `docs/product/locked-decisions.md`.
- Kleine tracking/wordingdrift hersteld in `docs/product/current-state.md` (titel + samenvattingsregel nu post-Task-104).
- Compacte notitie toegevoegd: `docs/product/read-only-readiness-terminology-lock-check-task-105.md`.
- Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.

## Task 103 — conservatieve read-only product-doc consistency follow-up (documentation-only)

- Status: afgerond.
- Productdocs gecontroleerd op post-Task-102 tracking/wordingdrift tegen de vergrendelde termenset in `docs/product/locked-decisions.md`.
- Gerichte documentatiefixes uitgevoerd (current-state tracking + backlog/next-step logging) en compacte checknotitie toegevoegd: `docs/product/read-only-readiness-consistency-check-task-103.md`.
- Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.



| Task 108 non-runtime foundation preflight | Contracted | N/A | N/A | N/A | Runtime pending | Grote documentatie/design-preflight uitgevoerd met kandidatenmatrix en exact één aanbevolen Task 109 (request-log/provider-metadata/freshness-audit contract preflight). Geen runtime-fetching/scheduler/AI/suggesties/Decision Packages/actiedrafts/orders/fake data. |

## Task 107 sustainability tracking guardrail (documentation/review-hardening only)

- Status: afgerond.
- Post-Task-106 producttracking gecontroleerd tegen de vergrendelde read-only terminology in `docs/product/locked-decisions.md`.
- Kleine trackingdrift gecorrigeerd in `docs/product/current-state.md` (titel + `Huidige toestand:`).
- Compacte sustainability-checknotitie toegevoegd: `docs/product/read-only-readiness-sustainability-check-task-107.md`.
- Tracking-drift preventieregel toegevoegd aan `docs/product/project-handover.md` en `docs/product/codex-ci-quality-rules.md` als documentatie/review discipline (geen CI-automatisering).
- Geen runtime market-data fetching, runtime-fetch, latest-price fetching, scheduler/background jobs, forecast runtime, AI runtime, suggesties, Decision Packages runtime, actiedrafts, orders of fake data toegevoegd.


- Task 113 afgerond: read-only audit summary/count contracten + usability verbeteringen; geen runtime-unlock.


- Task 114 afgerond: read-only audit linked-record coverage/navigation hardening en web type-alignment; geen runtimegedrag toegevoegd.

- Task 117 toegevoegd: typed provider boundary (domain) voor read-only market-data snapshots met conid-identiteitsvalidatie, zonder runtime-fetch unlock.

- Task 123 scope verwerkt: alleen read-only IBKR paper account/cash/positions sync via handmatige trigger; geen orderruntime.
- Task 125B verwerkt: storage repository dataclasses/methodes voor duurzame IBKR sync snapshot-tabellen bestaan nu; API/runtime wiring blijft pending voor Task 125C.
## Task 125B update: durable IBKR sync storage repository layer completed; API/runtime wiring deferred to 125C.

| Task 125C-A IBKR sync persistence scaffolding | Contracted | Task 125B storage records/repository methods hergebruikt | API implemented (pure mapper helpers + kleine persistence-façade) | UI N/A | Runtime pending | Geen endpoint runtime replacement; huidige `/ibkr/sync` en snapshot endpoints blijven bestaande behavior gebruiken; geen IBKR netwerkcode/TWS-Gateway connectiecode/orders/suggesties/Decision Packages/AI runtime/forecasting/scheduler/market-data runtime/fake data. |

- Task 125D: **completed** — read-only portfolio valuation voorbereiding toegevoegd vanuit duurzame IBKR sync snapshots, met expliciete blocked/control-needed status bij ontbrekende of verouderde marktdata. Geen market-data runtime, geen suggesties, geen action drafts, geen broker orders/execution en geen fake prijzen toegevoegd.

| Task 125E cash/FX valuation readiness enrichment | Completed | Hergebruik bestaande IBKR sync + cash snapshots | API contract uitgebreid met read-only cash/FX readiness, geen runtime FX/market fetch | UI ongewijzigd | Runtime pending | Geen suggesties/action drafts/orders, geen fake cash/FX/totals; expliciete blocked/control-needed statussen. |

| Task 125F FX snapshot contract inventory/readiness linkage | Completed | Inventaris van bestaande storage/API contracten | API valuation readiness uitgebreid met expliciete FX-opslagcontractstatus (`fx_snapshot_contract_missing` wanneer afwezig) | UI ongewijzigd | Runtime pending | Geen FX runtime fetch/market-data runtime/suggesties/action drafts/orders; geen fake FX rates of converted totals. |


- Task 125H afgerond: FX snapshot durable storage foundation (read-only, no runtime fetch).

- In scope afgerond: Task 125I read-only consumption van opgeslagen FX snapshots in valuation readiness; buiten scope gebleven: runtime FX/provider fetch, market-data runtime, unsafe conversion totals, suggesties/action drafts/orders.


- Task 125L afgerond: read-only wiring van Decimal-only conversion-total calculator in valuation readiness endpoint; alleen opgeslagen inputs, zonder runtime FX/provider fetch, zonder market-data runtime en zonder suggestions/action drafts/orders.
- Task 125N afgerond: read-only UI voor valuation conversion totals display geïmplementeerd met hergebruik van bestaande readiness endpoint-respons; runtime blijft pending; suggestie/IBKR/orderstatus blijft geblokkeerd; geen nieuwe berekeningen, geen runtime fetch en geen brokergedrag toegevoegd.
- Task 125O afgerond: advanced read-only valuation trace/details display UI geïmplementeerd voor valuation conversion totals; bestaande `GET /portfolio/valuation/readiness` endpoint-respons hergebruikt; runtime blijft pending; suggestie/IBKR/orderstatus blijft geblokkeerd; geen nieuwe berekeningen, geen runtime fetch en geen brokergedrag toegevoegd.
- Task 125O-R afgerond: web build repair-only na Task 125O; geen scope-uitbreiding en geen runtimewijziging.
| Task 125R cost-basis/unrealized P-L readiness wiring | Completed | Hergebruik van opgeslagen IBKR/market/FX inputs + Task 125Q calculator | API implemented (read-only wiring in `GET /portfolio/valuation/readiness`) | UI pending (geen 125S-display in deze taak) | Runtime pending | Geen runtime market-data/latest-price fetching, geen runtime FX/provider fetch, geen suggesties/action drafts/orders, geen broker execution, geen fake kostbasis/P-L/markt/FX/converted-total data. |
| Task 125R-R Optional Decimal mypy repair | Completed | N/A | API typing repair-only (geen behaviorwijziging) | UI N/A | Runtime pending | Focused repair na 125R; geen runtime scope-uitbreiding en geen nieuwe dataflows. |
| Task 125S read-only kostbasis/unrealized P-L display | Completed | Bestaande readiness-row velden uit `GET /portfolio/valuation/readiness` | API unchanged (web type contract uitgebreid met rows) | UI implemented (Portefeuille read-only tabel) | Runtime pending | Geen browser-side financiële berekeningen; geen API behavior/storage/migraties; geen runtime fetch/suggesties/action drafts/orders/broker execution; geen fake waarden. |
| Task 125T read-only advanced kostbasis/unrealized P-L trace/details display | Completed | Bestaande readiness-row trace/blocker velden uit `GET /portfolio/valuation/readiness` | API unchanged (web type contract uitgelijnd met bestaand Python model) | UI implemented (row-level details in Portefeuille tabel) | Runtime pending | Geen browser-side financiële berekeningen; geen API behavior/storage/migraties; geen runtime fetch/suggesties/action drafts/orders/broker execution; geen fake waarden. |
| Task 125U valuation readiness UI-tekst/helptekst preflight review | Completed | Inventaris van bestaande valuation readiness labels/helpteksten/trace-empty staten | API unchanged | UI unchanged (documentatie-only) | Runtime pending | Document-first: consistente eenvoudige NL wording-catalogus + missing-input/trace-empty checklist; geen runtime/API behavior/storage/migraties/fetch/suggesties/action drafts/orders/broker execution/fake waarden. |

- Task 125P afgerond: document-first/read-only preflight voor cost-basis en unrealized P/L display rules toegevoegd op basis van opgeslagen IBKR snapshots + bestaande market/FX readiness gates; geen berekeningen, geen API/web UI-behavior changes, geen runtime FX/provider fetch, geen market-data runtime, geen latest-price fetching, geen suggesties/action drafts/orders en geen fake kostbasis/P-L/FX/converted totals.
- Task 125M afgerond: document-first/read-only UI/API display contract preflight voor valuation conversion totals toegevoegd (`docs/product/valuation-conversion-total-display-contract-preflight-task-125m.md`); geen web UI behavior changes, geen API behavior changes, geen runtime FX/provider fetch, geen market-data runtime, geen suggesties/action drafts/orders en geen fake FX-rates/converted totals.
