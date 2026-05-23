# Task 134B — Wire IBKR read-only sync readiness/preflight gate into manual sync execution blocking

- Gebruik de Task 133B statusgate om handmatige `POST /ibkr/sync/run` execution veilig te blokkeren wanneer readiness niet voldoet.
- Scope: alleen execution blocking op bestaande handmatige sync trigger met behoud van safety booleans en read-only paper-only gates.
- Geen real TWS/Gateway network runtime, geen account/portfolio sync runtime, geen market-data runtime, geen suggesties, geen action drafts en geen orders.

## Boundaries (locked)
- Geen real TWS/Gateway network runtime.
- Geen account/portfolio sync runtime.
- Geen market-data runtime.
- Geen suggesties.
- Geen action drafts.
- Geen orders (submit/modify/cancel/bind).
- Geen broker execution.
- Geen fake brokerdata, fake portfoliodata of fake marktdata.
