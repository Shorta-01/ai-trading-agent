# Task 150 — IBKR TWS/Gateway client dependency CI preflight (install/import only)

## 1. Purpose
Valideren dat de geselecteerde clientdependency `ibapi` veilig aan de API package metadata kan worden toegevoegd en in CI kan installeren/importeren, zonder runtime connectiviteit.

## 2. Current state after Task 149
Task 149 leverde een documentatie-only compatibiliteitspreflight op met aanbeveling voor `ibapi` als kleinste en veiligste volgende dependency-only stap.

## 3. Selected candidate
Geselecteerde kandidaat: `ibapi`.
Niet geselecteerd en niet toegevoegd: `ib_insync`.

## 4. Dependency metadata change
`ibapi==9.81.1.post1` is toegevoegd aan `apps/api/pyproject.toml` onder API dependencies.

## 5. Install/import preflight design
- CI gebruikt de bestaande API-installatieflow (`pip install -e .[dev]`).
- Nieuwe smoke test importeert alleen veilige `ibapi` modules.
- Test monkeypatcht `socket.socket.connect` zodat elke onverwachte connectiepoging direct faalt.
- Geen connect-methodes aangeroepen, geen event loop, geen runtime clients.

## 6. CI coverage
Geen nieuwe CI-job toegevoegd. De bestaande `api` job dekt installatie + tests van deze preflight.

## 7. What was tested
- API metadata bevat `ibapi` en bevat geen `ib_insync`.
- `import ibapi` en `import ibapi.wrapper` slagen.
- Tijdens import wordt geen socket connect geprobeerd.
- Productiecode onder `apps/api/src/portfolio_outlook_api` importeert geen `ibapi` of `ib_insync`.
- Bestaande runtime-disabled/readiness tests blijven groen.

## 8. What was not tested
- Geen runtime TWS/Gateway connectiviteit.
- Geen account/portfolio sync runtime.
- Geen market-data runtime of FX runtime.
- Geen suggestions/action drafts/orders/broker execution.

## 9. Production import boundary
`ibapi` mag nu in dependency metadata en preflight-tests bestaan, maar wordt nog niet door productie-runtime modules geïmporteerd.

## 10. Runtime safety boundary
Runtime gates blijven disabled-by-default. Geen runtime unlock of endpoint-semantiekwijziging.

## 11. No-socket/no-connection guarantee
De preflight importtest faalt expliciet als `socket.connect` wordt aangeroepen. Daardoor is import-only gedrag afgedwongen zonder verbinding.

## 12. Rollback plan
Als dependency-install/import in CI faalt:
1. verwijder `ibapi` uit `apps/api/pyproject.toml`;
2. verwijder preflight test;
3. zet opvolgtaak naar Task 150-R (rollback naar dependency-free boundary).

## 13. Results
Resultaat: geslaagd. `ibapi` dependency preflight toegevoegd zonder runtime-connectiviteit of productie-imports.

## 14. Recommended next task
Task 151 — Add dependency-isolated `ibapi` client façade module with no connection behavior and no production runtime wiring.
