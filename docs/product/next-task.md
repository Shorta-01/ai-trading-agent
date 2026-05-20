# Next Task

## Blocker first (required)

CI is momenteel geblokkeerd door een GitHub Actions execution/logging probleem dat eerder ook in de minimale diagnostische workflow optrad. Die tijdelijke workflow is intussen verwijderd na bevestiging van dezelfde blokkade zonder bruikbare logs/artifacts. Eerst herstellen:

1. GitHub Actions repository/settings controleren.
2. Billing/quota limieten controleren.
3. Runner-beschikbaarheid en permissies controleren.
4. Log/artifact-toegang herstellen zodat failures weer diagnoseerbaar zijn.

Zolang CI rood blijft en diagnostische logging ontbreekt:

- geen blind codeherstel;
- geen featurewerk;
- **Task 89 blijft geblokkeerd**.

## Daarna pas

Task 89 — Conservatieve API-readiness contract hardening: kleine vervolgstap met extra response-contract regressietests en expliciete typed coverage voor snapshot-detailvarianten (read-only, geen runtime).
