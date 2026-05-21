# Ai Trading Agent — Version 1 Scope Register

Zie ook `docs/product/final-solution-vision.md` voor het einddoel.

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

| Portfolio sync from IBKR | Core workflow | Planned | Planned | UI pending | Runtime pending | Geen runtime-implementatie; IBKR blijft operationele waarheid |
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
- Geen real-money execution.
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
| Centrale IBKR Gateway skeleton (read-only/safe boundary) | Planned | Sessiebeheer, auth/account-mode status, keepalive, logging, pacing, paper-only enforcement. |
| Market-data pacing/freshness hardening | Planned | Geen fetch-unlock zonder freshness/quality gates; geen zero-fill of stale-hergebruik als fresh. |
| Deterministisch usable-cash contract | Planned | Buying power is geen veilige cash; cashberekening volledig auditeerbaar. |
| AI enforcement foundation | Planned | Schema-validatie + evidence-linking + safety gates vóór AI-impact op beslissingen. |
| Decision Package storage/API/UI | Planned | Verplicht vóór suggestions; immutable/auditable beslissingscontext. |
| Paper action state machine + IBKR reply handshake | Planned | Verplicht vóór toekomstige paper submission flow; Version 1 blijft paper-only. |

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
| V1.8 paper action workflow | Planned / **Paper-only future** |

Extra lock: suggestions/action drafts blijven blocked tot data/model/evidence/freshness/risk gates + approved modelversion actief zijn.

- In scope afgerond: AssetListing identity foundation als aparte laag naast AssetMaster, inclusief listing-level IBKR conid representatie en blocked-by-default safetyvelden.


- Task 94 (completed): watchlist API exposeert nu read-only AssetListing readiness/status per `ibkr_conid`; unresolved/unvalidated listings blijven hard geblokkeerd voor market data/analysis/suggesties/action drafts; geen runtime market-data/forecast/AI/actions/orders toegevoegd.

- Task 95 (completed): market-data readiness list/detail bevat expliciete typed AssetListing validation-gate status in read-only contract; missing/unvalidated listing blijft blocked; validated listing blijft status-only zonder runtime-fetch. Geen runtime market-data/forecast/AI/suggesties/Decision Packages/action drafts/orders toegevoegd.

| Task 96 readiness/watchlist/latest-snapshot terminologieharmonisatie | Contracted | Bestaande storage-read contracten hergebruikt | API implemented (geharmoniseerde read-only NL boundary-terminologie + regressietests) | UI N/A | Runtime pending | Geen market-data runtime/fetching/historical/scheduler/forecast/AI/suggesties/Decision Packages/action drafts/orders; latest snapshot blijft metadata/status-only; missing/unvalidated listings blijven blocked. |


| Task 98 read-only readiness UI/API contract inventory | Contracted | N/A | N/A | N/A | Runtime pending | Documentatie/inventaris-only guardrail voor labelconsistentie in resterende schermen + readiness-contracten; geen runtime market-data/latest-price fetching/scheduler/forecast/AI/suggesties/Decision Packages/action drafts/orders/fake data. |
