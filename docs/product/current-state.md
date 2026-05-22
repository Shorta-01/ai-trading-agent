- Task 125B: **completed** — PR #258 heeft de IBKR sync storage repository-laag toegevoegd voor vijf duurzame read-only snapshot-tabellen: `ibkr_sync_runs`, `ibkr_account_cash_snapshots`, `ibkr_position_snapshots`, `ibkr_open_order_snapshots` en `ibkr_execution_snapshots`. Toegevoegd zijn repository-dataclasses/records, SQL repository-methodes (`save/get/list/latest`), publieke exports en storage-tests inclusief Decimal round-trip, `None`-preservatie en safety booleans die `false` blijven. Task 125B heeft **geen** API/runtime persistence wiring toegevoegd; dat blijft deferred naar Task 125C.
- Scopebevestiging Task 125B: geen orders, geen suggesties, geen AI runtime, geen forecasting, geen fake brokerdata, geen fake marktdata en geen paid-subscription-afhankelijke IBKR-features toegevoegd.
- Task 125A-R: **completed** — CI-herstel na PR #256 door IBKR sync snapshot migratieconsistentie te repareren (revisie 0025, inventory-contract, metadata-set en tests). Dit bevestigt dat Task 125A alleen duurzame read-only schema/metadata/migration foundation toevoegde; repository-dataclasses/methodes en API runtime wiring bleven toen expliciet deferred naar Task 125B.

# Current State (na Task 125B)

- Task 122: **completed** — IBKR TWS/Gateway technical preflight documentatie toegevoegd en read-only IBKR sessiestatuscontract uitgebreid (disabled-by-default, geen auto-connect, geen orders, safety booleans false).

- Task 120: **completed** — disabled-by-default IBKR paper marktdata-adapter skeleton en handmatige latest-snapshot fetch route toegevoegd (status-first, read-only, geen scheduler/background fetch, geen fake data, safety booleans false).

# Current State (na Task 120)

## 1) Current status summary

- Task 117: **completed** — eerste market-data foundation slice gestart met typed domain provider boundary voor read-only snapshotopvraging op conid-identiteit en expliciete blocked status bij ontbrekende/ongevalideerde identiteit. Scope blijft conservatief: geen live trading, geen orders, geen suggesties en safety booleans blijven false.

- Task 115: **completed** — audit viewer status-quality en contractconsistentie verhard met auditketen/metadata-kwaliteit velden in API, lijstsamenvattingen, regressietests tegen model/dataclass-drift, en web-overview/detail zichtbaarheid. Scope bleef strikt read-only/non-runtime; geen provider calls, runtime-fetch, market-data runtime, suggesties, actiedrafts, orders, IBKR connectie/orders of fake data. CI baseline gecontroleerd vóór implementatie op run #461 (alle zes jobs groen).

- Task 114: **completed** — linked-record API regressiedekking toegevoegd voor request-audit responsemodellen, auditoverzicht verhard met zichtbare read-only recordkaarten en detaillinks, detail-fallbacknavigatie verbeterd, web API types uitgelijnd met Task 113H contract. Scope bleef strikt read-only/non-runtime zonder provider calls, market-data runtime, runtime-fetch, latest-price fetching, scheduler/background jobs, historical fetching, forecast runtime, AI runtime, suggesties, Decision Packages runtime, actiedrafts, IBKR connectie/orders of fake data. CI-check vóór implementatie vastgelegd op run #455 baseline (GitHub API niet bereikbaar in deze omgeving).


- Task 110E: **completed** — resterende Task 110 scope afgerond met read-only/status API exposure voor request logs, provider/source metadata en freshness-audit records inclusief API tests en producttracking-updates. Task 110 is hiermee volledig afgerond: metadata-tabellen, Alembic migratie 0023, migration readiness registration, repository dataclasses/protocols, SQL repository skeleton, public exports, storage tests, read-only/status API endpoints en API tests. Alles blijft non-runtime; geen provider calls, geen market-data runtime, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical fetching, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen IBKR connectie/orders en geen fake data toegevoegd. Safety booleans blijven conservatief false/blocked.

- Task 109: **completed** — documentatie/design-only contract preflight afgerond (`docs/product/request-log-provider-freshness-contract-preflight-task-109.md`). Candidate contractcatalogi vastgelegd voor request logs, provider/source metadata en freshness-audit records inclusief status/reason-code proposals, traceability-linking en readiness-relatiemapping. Geen storagetabellen, migrations, endpoints, schedulers, runtime-fetching, latest-price fetching, forecast runtime, AI runtime, suggesties, Decision Packages runtime, actiedrafts, orders of fake data toegevoegd. Task 107 tracking-drift preventieregel expliciet gevolgd.

-  Task 108: **completed** — grote conservatieve non-runtime implementatie-prep audit afgerond (`docs/product/non-runtime-foundation-preflight-task-108.md`). Exact één betekenisvolle Task 109 aanbevolen (request-log/provider-metadata/freshness-audit storage/API contract preflight, documentatie/design-only). Task 107 tracking-drift preventieregel expliciet gevolgd (current-state titel + Huidige toestand + completionregel + task-history + scope-register + backlog + next-task in dezelfde PR geüpdatet). Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical fetching, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.

- Task 81 is documentation-only en vergrendelt dat actieve Volglijst-items IBKR-contract-based moeten zijn.
- Task 81 voegt geen IBKR-runtime toe.
- Task 81 voegt geen market-data runtime toe.
- Task 81 voegt geen historische data-fetching toe.
- Task 81 voegt geen schedulers toe.
- Task 81 voegt geen suggestions, Decision Packages, action drafts, AI runtime of ordergedrag toe.
- Claude architecture/roadmap audit is reviewed; geaccepteerde findings zijn opgenomen in roadmap/todo-documentatie.
- Task 88I is documentatie-only; geen runtimegedrag gewijzigd.
- Huidige toestand: **na Task 125B**.
- Task 101: **completed** — documentatie/cross-link/terminologie-anchor-only update. Task 100-termenset is verankerd in handover + locked decisions + lichte cross-links. Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages/action drafts/orders en geen fake data toegevoegd.
- Task 102: **completed** — conservatieve documentatie-only read-only wording drift check na Task 101. Productdocs zijn gecontroleerd tegen de vergrendelde termenset in `locked-decisions.md`; kleine tracking/plaatsingsdrift is hersteld (current-state titel + backlogplaatsing/next-step wording). Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages/action drafts/orders en geen fake data toegevoegd.
- Task 103: **completed** — conservatieve documentatie-only product-doc consistentiecheck na Task 102. Productdocs zijn gericht gecontroleerd tegen de vergrendelde read-only terminology in `locked-decisions.md`; kleine tracking/wordingdrift is hersteld (current-state na-Task-102 tracking + follow-up logging). Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages runtime/actiedrafts/orders en geen fake data toegevoegd.

- Task 104: **completed** — conservatieve documentatie-only tracking consistency mini-follow-up na Task 103. Producttrackingdocs zijn gecontroleerd tegen de vergrendelde read-only terminology in `locked-decisions.md`; kleine trackingdrift is gericht hersteld (current-state na-Task-103 status). Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.

- Task 107: **completed** — conservatieve documentatie/review-hardening sustainability-check na Task 106. Post-Task-106 producttracking is gecontroleerd tegen de vergrendelde read-only terminology in `locked-decisions.md`; bekende trackingdrift is hersteld (current-state naar post-Task-106) en compacte tracking-drift preventieregel is toegevoegd in productdocs. Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.
- Task 106: **completed** — conservatieve documentatie-only read-only terminology lock discipline follow-up na Task 105. Post-Task-105 producttrackingdocs zijn gericht gecontroleerd tegen de vergrendelde read-only terminology in `locked-decisions.md`; kleine tracking/wordingdrift is hersteld (current-state titel + samenvattingsregel naar post-Task-105 status). Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.
- Task 105: **completed** — conservatieve documentatie-only read-only terminology lock check follow-up na Task 104. Producttrackingdocs zijn gericht gecontroleerd tegen de vergrendelde read-only terminology in `locked-decisions.md`; kleine tracking/wordingdrift is hersteld (current-state titel + samenvatting naar post-Task-104 status). Geen runtime market-data fetching, geen runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties, geen Decision Packages runtime, geen actiedrafts, geen orders en geen fake data toegevoegd.
- CI-status: **hersteld en groen** na repository visibility change naar public; GitHub Actions execution/logging is weer zichtbaar en bruikbaar.
- Projectstatus: nog foundation-heavy; Version 1 is niet compleet.
- Meest volwassen deel: Onderzoeksbibliotheek / Research Library foundations.
- Suggestion runtime, probabilistische forecast runtime, AI runtime, market-data runtime en IBKR runtime bestaan nog niet.
- Moderne web app shell + dashboard foundation bestaat nu met eerlijke empty states (geen fake data).

- Task 95: **completed** — read-only market-data readiness / AssetListing validation-gate harmonisatie afgerond (API/tests/docs). Readiness list/detail responses bevatten nu expliciet typed `asset_listing_gate` met statusvarianten `storage_unavailable`, `missing_ibkr_conid`, `missing_listing`, `unvalidated_listing`, `validated_listing` en eenvoudige Nederlandse status/next-step/audit-tekst. Missing of unvalidated AssetListing blijft market data/analysis/suggesties/action drafts blokkeren; gevalideerde AssetListing blijft identity/status-only en start geen runtime market-data fetching. Geen market-data runtime/fetching/historical/scheduler/forecast runtime/AI runtime/suggesties/Decision Packages/action drafts/IBKR-ordergedrag/fake data toegevoegd.



- Task 97: **completed** — API model-documentatie/type-metadata + web UI labelconsumptie + tests/docs hardening voor read-only readiness boundaries afgerond. Volglijst gebruikt nu `asset_listing_readiness.status_nl` + `next_step_nl` als hoofdstatus. Geen market-data runtime of runtime-fetch, geen latest-price fetching, geen scheduler/background jobs, geen historical/forecast/AI runtime, geen suggesties/Decision Packages/action drafts/orders en geen fake data toegevoegd.

- Task 96: **completed** — conservatieve read-only terminologieharmonisatie afgerond voor watchlist AssetListing readiness, market-data readiness AssetListing-gate en latest-snapshot responses (API/tests/docs). NL boundary-tekst is nu geharmoniseerd rond read-only status: geen market-data runtime, geen runtime-fetch, geen analysevrijgave, geen suggesties, geen Decision Packages, geen actiedrafts en geen orders. Latest snapshot blijft metadata/status-only (geen live/current prijs). Missing/unvalidated AssetListing blijft blocked; validated AssetListing blijft identity/status-only. Geen market-data runtime/fetching/historical/scheduler/forecast runtime/AI runtime/suggesties/Decision Packages/action drafts/IBKR-ordergedrag/fake data toegevoegd.


- Task 98: **completed** — documentatie/inventaris-only read-only readiness UI/API contractinventaris toegevoegd (`docs/product/read-only-readiness-ui-contract-inventory.md`) voor resterende schermen en readiness-contracten. Labelpatronen voor "veilig", "onveilig tenzij ontkend" en follow-up governance zijn expliciet vastgelegd. Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages/action drafts/orders en geen fake data toegevoegd.

- Task 99: **completed** — documentatie/review-guardrail-only hardening toegevoegd met compacte PR-checklist + term-review rubric (`docs/product/read-only-readiness-pr-checklist.md`) en koppeling vanuit de read-only readiness inventaris/CI kwaliteitsregels. Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages/action drafts/orders en geen fake data toegevoegd.
- Task 100: **completed** — beperkte product-doc terminologie-audit uitgevoerd buiten de UI/API-inventaris; nieuw auditnote-document toegevoegd (`docs/product/read-only-readiness-product-doc-terminology-audit.md`) en stale read-only readiness trackingterminologie geharmoniseerd waar nodig. Geen runtime market-data fetching, geen latest-price fetching, geen scheduler/background jobs, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages/action drafts/orders en geen fake data toegevoegd.

## 2) Implemented foundations

### Platform foundations

- Repository/API/worker/web/docker/CI skeleton bestaat.
- Settings/status foundations bestaan.
- System events foundation bestaat.
- IBKR contracts/placeholders bestaan (geen runtime verbinding).
- Probabilistische asset-outlook doctrine staat vast in docs.
- CI quality rules staan vast in docs.

### Research Library foundations (implemented)

- Research source archive storage/API/UI foundations.
- Safe file upload.
- TXT/MD/CSV extraction.
- Extraction UI trigger + statusweergave.
- Deterministische documentclassificatie.
- Prompt-injection scan status storage/API foundation.
- Source credibility assessment status storage/API foundation.
- Source evidence item storage/API foundation.
- Evidence Ledger linking foundation.
- Gate outcome/freshness foundation.
- Source conflict detection foundation.
- Asset master identity foundation (storage/API) bestaat als referentie/status-only basis.
- Source-to-asset linking foundation (storage/API) bestaat als audit/reference/status-only basis.

## 3) Safety and behavior state now

- Alle source/evidence outputs blijven **blocked for suggestions**.
- Source conflict findings zijn **audit/status-only**.
- Conflict findings blijven **blocked for suggestions**.
- Geen runtime suggestions.
- Geen AI runtime.
- Geen watchlist insertion behavior.
- Geen portfolio positions behavior.
- Geen IBKR runtime action behavior.
- Geen market-data runtime.
- Geen forecast runtime.
- Geen order behavior.

## 4) Current non-complete areas (accurate)

- Prompt-injection runtime scanning engine: pending (alleen status storage/API bestaat).
- Source credibility runtime scoring engine: pending (alleen status storage/API bestaat).
- Evidence ledger runtime/API-linking verdieping: pending.
- PDF/DOCX/XLSX/PPTX extractie: pending.
- OCR: pending.
- URL fetch + veilige snapshotting: pending.
- Source conflict detection runtime engine: pending.
- Source freshness/runtime validation: pending.
- Asset detection from sources: pending.
- Source-to-asset linking runtime/detection/matching beyond foundation: pending.
- Market data/freshness runtime validation: pending.
- Watchlist proposal/user-confirm flow: pending.
- Suggestion engine runtime: pending.
- Probabilistische forecast runtime: pending.
- Portfolio/watchlist volledige runtime grids: pending.
- IBKR read-only runtime integratie: pending.
- IBKR paper action flow/submission/reconciliatie: pending.
- Audit viewer runtime: pending.
- AI Event Intelligence runtime: pending.
- Belgische tax/compliance runtime: pending.
- Deployment backup/restore hardening met restore-test bewijs: pending.

## 5) Latest task sequence status


- Task 94: **completed** — AssetListing-to-watchlist readiness wiring afgerond (API/tests/docs): watchlist list/detail responses bevatten nu een typed read-only `asset_listing_readiness` contract dat AssetListing-status per `ibkr_conid` koppelt met deterministische statussen (`missing_listing`, `unvalidated_listing`, `validated_listing`, `storage_unavailable`) en Nederlandse status/next-step/audit-teksten. Ook bij gevalideerde listing blijven `market_data_ready=false`, `analysis_ready=false`, `suggestions_allowed=false` en `action_drafts_allowed=false`; runtime market-data fetch/scheduler, forecast runtime, AI runtime, suggesties, Decision Packages, action drafts en ordergedrag blijven buiten scope. AssetListing blijft strikt gescheiden van AssetMaster; tickertekst alleen blijft onvoldoende.
- Task 92: **completed** — conservatieve market-data readiness explainability en boundary-consistency hardening afgerond: list/detail/latest-snapshot responses bevatten nu stabiele NL help/status-teksten en expliciete non-implication boundaryvelden (`analysis_ready=false`, `suggestions_allowed=false`, `action_drafts_allowed=false`). Blocked/ready/snapshot-metadata semantiek is deterministischer en regressie-getest, inclusief detail endpoint en alle latest-snapshot varianten. Snapshotmetadata blijft read-only status/auditmetadata en impliceert geen analyse, suggesties, Decision Packages, action drafts of orders. Scope bleef read-only API-contract/test/docs hardening; geen market-data runtime, historical fetching, scheduler, AI runtime, suggesties, Decision Packages, action drafts, IBKR-ordergedrag of fake market/broker/recommendation data toegevoegd. Ongevalideerde of onopgeloste identiteiten blijven blocked voor market data/analysis/suggesties/action drafts.
- Task 91: **completed** — conservatieve market-data readiness status-normalisatie afgerond: list/detail readiness-statusvelden zijn nu expliciet getypeerd en genormaliseerd (`blocked`/`ready`, `missing_snapshot`/`snapshot_available`, `missing_or_unvalidated_ibkr_contract`) met regressietests op stabiele Nederlandse help/statusvelden en deterministische blocked/missing-snapshot paden. Latest-snapshot statusvarianten (`not_configured`, `missing_snapshot`, `snapshot_available`, `storage_failure`) blijven expliciet en getest. Scope bleef read-only API-contract/test hardening; geen market-data runtime, geen historical fetching, geen scheduler, geen AI runtime, geen suggesties/Decision Packages/action drafts/IBKR-ordergedrag en geen fake prices/broker/recommendations toegevoegd. Ongevalideerde of onopgeloste identiteiten blijven blocked voor market data/analysis/suggesties/action drafts.
- Task 90: **completed** — conservatieve market-data readiness API cleanup afgerond: snapshot-latest endpoint gebruikt nu expliciet typed responsecontract met vaste statusvarianten (`snapshot_available`, `missing_snapshot`, `not_configured`, `storage_failure`) en regressietests dekken not-configured/storage-failure/missing-snapshot + read-only metadata-only semantiek. Scope bleef read-only API-contract/test hardening; geen market-data runtime, geen historical fetching, geen scheduler, geen AI runtime, geen suggesties/Decision Packages/action drafts/IBKR-ordergedrag en geen fake prices/broker/recommendations toegevoegd. Ongevalideerde of onopgeloste identiteiten blijven blocked voor market data/analysis/suggesties/action drafts.
- Task 88L: **completed (documentation-only)** — CI-herstel vastgelegd na repository visibility change naar public. CI run #358 is groen met 6 geslaagde jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`); logs/steps weer zichtbaar. Geen code/tests/migraties/package metadata/workflows gewijzigd.
- Task 88G: **completed (documentation-only)** — historische diagnose van eerdere GitHub Actions execution/logging blokkade. Deze blokkade is intussen opgelost na visibility change naar public (zie Task 88L).

- Task 88: **completed** — API-only readiness-contract consolidatie voltooid: typed readiness responsemodellen/helpers gecentraliseerd (`market_data_readiness.py`), readiness-routes verdund en regressietests uitgebreid. Read-only scope behouden; geen market-data runtime, geen historical fetching, geen scheduler, geen AI runtime, geen suggesties/Decision Packages/action drafts/IBKR-ordergedrag en geen fake prices/broker/recommendations toegevoegd. Ongevalideerde of onopgeloste identiteiten blijven blocked voor market data/analysis/suggesties/action drafts.
- Task 88B: **completed** — CI/type/import-boundary repair na Task 88: `market_data_readiness.py` koppelt niet langer aan `watchlist.py` modelimport en gebruikt nu een minimale typed protocol-input voor readiness-row build. Dit voorkomt onnodige route/store dependency-koppeling in response-contract code. Geen runtimegedrag toegevoegd; geen market-data runtime, geen historical fetching, geen scheduler, geen AI runtime, geen suggesties/Decision Packages/action drafts of IBKR-ordergedrag toegevoegd. Geen fake market prices, brokerdata of aanbevelingen toegevoegd. Ongevalideerde/onopgeloste identiteiten blijven blocked voor market data, analyse, suggesties en action drafts.

- Task 68: **completed** — Evidence Ledger-linking foundation voor research-source evidence toegevoegd (storage/API), uitsluitend voor audit/lineage; suggesties blijven geblokkeerd.
- Task 69: **completed** — gate outcome/freshness foundation toegevoegd als storage/API basis (audit/status-only).
- Task 69B: **completed** — repair afgerond; CI opnieuw groen zonder runtimewijzigingen.
- Task 70: **completed** — source conflict detection foundation toegevoegd (storage/API), audit/status-only; suggesties blijven geblokkeerd.
- Task 70B: **completed** — API/storage pytest issues gerepareerd; CI groen; geen runtimegedrag gewijzigd.
- Task 71: **completed** — asset master identity foundation toegevoegd (storage/API), identity blijft referentie/status-only en geblokkeerd voor suggesties; geen watchlist/portfolio/suggestie/IBKR/order/AI/market-data/forecast runtime.
- Task 71B: **completed** — API mypy repair afgerond; CI opnieuw groen; geen runtimegedrag gewijzigd.

- Task 72: **completed** — source-to-asset linking foundation toegevoegd (storage/API), audit/reference-only naar canonical asset identities; blijft geblokkeerd voor suggesties en voegt geen watchlist/portfolio/AI/market-data/forecast/IBKR/order runtime toe.

- Task 72B: **completed** — storage mypy row-to-record typing en API pytest 503 failures gerepareerd; CI groen; geen runtimegedrag gewijzigd.
- Task 72C: **completed** — resterende API pytest source-link create→list fixture persistence failure gerepareerd; CI opnieuw groen; geen runtimegedrag gewijzigd.


- Task 74: **completed** — moderne GUI shell en dashboard foundation toegevoegd (apps/web) met Nederlandse navigatie, statusbadges, icon-tooltips, dashboardpanelen en veilige empty states. Geen IBKR runtime, geen market-data runtime, geen suggestion runtime, geen AI runtime, geen ordergedrag en geen fake portfolio/broker/suggestiedata toegevoegd.

- Task 75: **completed** — read-only IBKR portfolio sync foundation toegevoegd met veilige status/endpoints voor sync-run, posities en cash snapshots. Geen ordersubmission, geen action drafts, geen suggestions, geen Decision Packages, geen AI/market-data/forecast runtime en geen fake broker/portfolio data.


- Task 76: **completed** — read-only IBKR sync foundation uitgebreid met open-orders en executions/fills snapshots + endpoints. Geen ordersubmission, orderwijziging, ordercancel, action drafts, suggesties, Decision Packages, AI/market-data/forecast runtime en geen fake broker/order/execution data.
- Task 76B / PR #153: **completed** — API mypy repair op sync run count typing (`int`) met CI terug groen; geen runtimegedrag gewijzigd.
- Task 77: **completed** — read-only Portefeuille-grid toegevoegd op basis van opgeslagen IBKR snapshots (posities, cash, open orders, executions/fills) met Nederlandse empty/error/loading states. Geen echte IBKR connectieruntime, geen ordersubmission/-wijziging/-cancel, geen action drafts, geen suggesties, geen Decision Packages, geen AI/market-data/forecast runtime en geen fake broker/portfolio/order/execution data.

- Task 78: **completed** — watchlist foundation + Volglijst-pagina toegevoegd (lokaal/manueel, gescheiden van IBKR-portefeuille).
- Task 78B: **completed** — CI-repair na Task 78. Root causes: API ruff-formattingfouten in `watchlist.py` en `test_watchlist_endpoints.py`, plus stale storage testverwachtingen voor migratie-inventaris en metadata na `0020_watchlist_foundation.py` / `watchlist_items`. Geen runtimegedrag gewijzigd, geen nieuwe features toegevoegd; watchlist blijft lokaal/manueel en gescheiden van IBKR-posities. Geen suggesties, action drafts, IBKR-ordergedrag, AI runtime, market-data runtime, forecast runtime of fake data toegevoegd.


- Task 79: **completed** — watchlist-to-Asset-Master identity linking foundation toegevoegd (API/UI basis, reference/status-only). Linken/ontkoppelen valideert bestaande asset-identiteit waar veilig, zonder auto-creatie van Asset Master records. Geen portfoliopositiecreatie, geen suggesties, geen Decision Packages, geen action drafts, geen IBKR-ordergedrag, geen AI/market-data/forecast runtime en geen fake data.

- Task 80: **completed** — Asset Master search/picker foundation toegevoegd (read-only zoekendpoint + Volglijst picker UI) zodat gebruikers bestaande canonical asset-identiteiten kunnen zoeken, selecteren, linken en ontkoppelen voor watchlist-items. Reference/status-only: geen auto-creatie van Asset Master records, geen portfoliopositiecreatie, geen suggesties, geen Decision Packages, geen action drafts, geen IBKR-ordergedrag, geen AI/market-data/forecast runtime en geen fake data.

- Task 81: **completed** — documentation-only; IBKR-contract-based active watchlist rule vergrendeld, conid-based data-readiness rule vergrendeld en sync/freshness/performance-roadmap vergrendeld. Geen runtimecode gewijzigd.

- Task 82: **completed** — read-only IBKR contract search/validation foundation toegevoegd met veilige not-configured responses en genormaliseerde conid-gebaseerde contractkandidaten/validatieresultaten via API-endpoints. Geen market-data runtime, geen historische data-fetching, geen schedulers, geen suggestions/Decision Packages/action drafts, geen IBKR ordergedrag, geen AI/forecast runtime en geen fake data.


- Task 83: Volglijst add-flow omgezet naar IBKR contractpicker; actieve creatie vereist gevalideerde IBKR-contractidentiteit. Bestaande losse records zonder contract blijven niet-gevalideerd en niet klaar voor analyse. Geen market-data runtime, historical fetching, schedulers, suggesties, Decision Packages, action drafts, IBKR-ordergedrag, AI runtime, forecast runtime of fake data toegevoegd.

## Current CI status (restored)

- Repository visibility is aangepast van private naar public; de eerdere GitHub Actions execution/logging blokkade is daarmee opgelost.
- CI run **#358** is succesvol afgerond.
- Alle 6 normale CI-jobs zijn groen: `domain`, `storage`, `portfolio`, `api`, `worker`, `web`.
- GitHub Actions logs en step-output zijn opnieuw zichtbaar.
- Normale gate blijft gelden: nieuwe featuretaken starten alleen bij groene CI.

## Task 84 update

- Task 84 toegevoegd: read-only IBKR-watchlist import foundation (watchlists + instrument-preview + import-candidates op conid-basis).
- Geen IBKR watchlist create/update/delete/export, geen market-data runtime, geen suggestions/Decision Packages/action drafts/orders.
- Task 84C: API pytest-repair na PR #163 voltooid; root cause was uitsluitend test setup (foutief `dataclasses.replace()` op Pydantic `Settings` en ontbrekende IBKR-configuratiepatch in configured-path test), geen runtimegedrag gewijzigd en geen scope-uitbreiding.


## Task 85 update

- Task 85 voltooid: conservatieve market-data storage/freshness foundation toegevoegd (schema + status-only API readiness endpoint).
- Geen market-data runtime toegevoegd, geen historical fetching, geen scheduler, geen AI/suggesties/Decision Packages/action drafts/IBKR-ordergedrag.
- Geen fake market prices of fake broker/recommendation data toegevoegd.
- Ongevalideerde of onopgeloste identiteiten blijven geblokkeerd voor market data en latere analyse/suggesties/actie-drafts.

- Task 86: **completed** — market-data readiness persistence wiring uitgebreid met read-only detail toegang en snapshot-metadata endpointfundament. Geen market-data runtime, geen historical fetching, geen scheduler, geen AI runtime, geen suggesties/Decision Packages/action drafts/IBKR-ordergedrag en geen fake prijzen/data toegevoegd. Onopgeloste of ongevalideerde identiteiten blijven geblokkeerd.

- Task 86B: **completed** — API CI-repair na Task 86. Root cause: mypy type issue in market-data readiness detail endpoint waar `dict[str, object]["items"]` als iterabel gebruikt werd. Fix: type/boundary cleanup met interne typed row-builder; geen runtimegedrag toegevoegd. Geen market-data fetch/runtime, geen historical fetching, geen scheduler, geen AI runtime/suggesties/Decision Packages/action drafts, geen IBKR-ordergedrag en geen fake market/broker/recommendation data. Ongevalideerde/onopgeloste identiteiten blijven geblokkeerd voor market data, analyse, suggesties en action drafts.

- Task 87: **completed** — conservatieve watchlist/readiness inspectieverbetering toegevoegd met duidelijke Nederlandse blocker/missing-snapshot uitleg, auditvelden (`evaluated_at`, `missing_identity_fields`, `validation_status`, `next_step_nl`) en read-only snapshotmetadata-status in readiness responses. Geen market-data runtime, geen historical fetching, geen scheduler, geen AI runtime, geen suggesties/Decision Packages/action drafts/IBKR-ordergedrag en geen fake data toegevoegd. Ongevalideerde/onopgeloste identiteiten blijven geblokkeerd voor market data, analyse, suggesties en action drafts.

## Task 88J update (documentation-only)

- Task 88J uitgevoerd als documentatie-only roadmapuitbreiding.
- Geen runtimegedrag gewijzigd.
- Geen applicatiecode/tests/migraties/package metadata/workflows gewijzigd door functionele implementatie.
- CI is hersteld en groen (run #358; alle 6 jobs geslaagd).
- Task 89 mag als volgende implementatietaak weer doorgaan onder de normale groene-CI gate.

- Task 93: **completed** — AssetListing identity foundation verdiept met aparte `asset_listings` storage- en API-basis (identity/reference/status-only). AssetListing is expliciet gescheiden van AssetMaster; IBKR conid hoort op listing/instrumentniveau. Tickertekst alleen blijft onvoldoende voor actieve watchlist, market data, analyse, suggesties of action drafts. Onopgeloste/niet-gevalideerde listings blijven blocked (`safe_to_use_* = false`, `blocks_* = true`). Geen market-data runtime/fetching, geen scheduler, geen forecast runtime, geen AI runtime, geen suggesties/Decision Packages/action drafts/orders en geen fake market/broker/recommendation data toegevoegd.

- Task 123: **completed** — read-only IBKR paper account/cash/positions handmatige sync-foundation toegevoegd via expliciete manual trigger, disabled-by-default configuratie en safety booleans false; geen orders/suggesties/AI/fake brokerdata.
## Task 125B update: durable IBKR sync storage repository layer completed; API/runtime wiring deferred to 125C.
