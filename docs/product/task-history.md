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
