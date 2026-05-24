# Task 151 — dependency-geïsoleerde `ibapi` client façade zonder connectiegedrag

Geselecteerde volgende taak: **Task 151**.

## Doel
Introduceer een dependency-geïsoleerde `ibapi` façade-module zonder socket/connectiegedrag en zonder production runtime wiring.

## Scope
- Voeg een kleine façade/interface module toe voor toekomstig `ibapi` gebruik.
- Geen runtime wiring naar endpoints of actieve statuschecks.
- Behoud disabled-by-default runtime boundary.

## Non-goals
- Geen TWS/Gateway connecties.
- Geen sockets openen.
- Geen auto-connect/reconnect loop.
- Geen persistente session manager.
- Geen account/portfolio sync runtime.
- Geen market-data runtime of FX runtime.
- Geen suggestions, action drafts, orders of broker execution.
