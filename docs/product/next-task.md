# Task 149 — dependency-selectie compatibiliteitspreflight zonder runtime-connectiviteit

Geselecteerde volgende taak: **Task 149**.

## Doel
Voer een documenteerde en testbare compatibiliteitspreflight uit voor kandidaat TWS/Gateway client libraries (`ibapi`, `ib_insync`) zonder runtime-connectiviteit, zodat een veilige dependencykeuze in een volgende stap onderbouwd kan worden.

## Scope
- Install/import-compatibiliteit vergelijken voor `ibapi` en `ib_insync` (Python/CI/arm64 risico’s).
- Geen runtime clientintegratie, geen connectiepogingen, geen sockets.
- Acceptance-rapport opleveren met duidelijke go/no-go criteria voor latere dependency-introductie.

## Non-goals
- Geen runtime code.
- Geen API/web/storage schemawijzigingen.
- Geen dependency toevoegen aan projectmetadata.
- Geen echte TWS/Gateway runtime, geen auto-connect/reconnect, geen session manager.
- Geen account/portfolio sync runtime, market-data runtime, FX runtime, suggesties, action drafts, orders of broker execution.
