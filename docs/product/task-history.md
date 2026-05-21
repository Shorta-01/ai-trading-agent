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
