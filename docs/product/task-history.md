# Task History (concise)

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
