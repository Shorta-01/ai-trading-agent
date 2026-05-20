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


## Task 70/70B status lock

- **Task 70:** source conflict detection foundation toegevoegd (storage/API), audit/status-only.
- **Task 70B:** API response-shape test en stale migration-readiness tests gerepareerd.
- **CI-status na Task 70B:** groen op main.
- **Runtime-impact van Task 70B:** geen runtimegedrag gewijzigd.
- **Suggestion-status:** conflict findings blijven geblokkeerd voor suggesties.
\n\n- Task 71: asset master identity foundation toegevoegd; identity is alleen referentie/status data, geen watchlist/portfolio/suggestie/IBKR/order/AI/market-data/forecast runtime.


- **Task 71B:** repair na Task 71-merge voor API mypy failure. Root cause: `asset_master.py` importeerde private helper `_get_repository` uit `research_sources.py`, waardoor mypy faalde met `attr-defined`. Fix: dependency boundary hersteld door repository-toegang lokaal en expliciet binnen `asset_master.py` af te handelen zonder private cross-route import. Runtimegedrag niet gewijzigd; asset identity records blijven referentie/status-only en geblokkeerd voor suggesties.
