# Task 130 — Add disabled-by-default IBKR TWS/Gateway read-only session-status adapter boundary and API status exposure

- Implementeer een kleine veilige Milestone B runtime-slice voor read-only sessiestatus, met adapter boundary + API status exposure.
- Gebruik geconfigureerde settings en eenvoudige Nederlandse status/helptekst.
- Houd behavior strikt disabled-by-default; geen auto-connect bij startup.

## Boundaries (locked)
- Geen account/portfolio sync in deze taak.
- Geen market-data runtime.
- Geen suggesties.
- Geen action drafts.
- Geen orders (submit/modify/cancel/bind).
- Geen fake brokerdata.
- Geen credentials in logs/API.

## CI and merge discipline
- Volg `docs/product/codex-red-green-ci-workflow.md`.
- Alleen handmatige merge na groene CI op alle zes jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
