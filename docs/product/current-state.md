# Current State (na Task 81)

## 1) Current status summary


- Task 81 is documentation-only en vergrendelt dat actieve Volglijst-items IBKR-contract-based moeten zijn.
- Task 81 voegt geen IBKR-runtime toe.
- Task 81 voegt geen market-data runtime toe.
- Task 81 voegt geen historische data-fetching toe.
- Task 81 voegt geen schedulers toe.
- Task 81 voegt geen suggestions, Decision Packages, action drafts, AI runtime of ordergedrag toe.
- Huidige toestand: **na Task 81**.
- CI-status: groen na Task 80.
- Projectstatus: nog foundation-heavy; Version 1 is niet compleet.
- Meest volwassen deel: Onderzoeksbibliotheek / Research Library foundations.
- Suggestion runtime, probabilistische forecast runtime, AI runtime, market-data runtime en IBKR runtime bestaan nog niet.
- Moderne web app shell + dashboard foundation bestaat nu met eerlijke empty states (geen fake data).

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
