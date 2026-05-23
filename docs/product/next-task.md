# Task 131 — Add read-only IBKR account-mode verification status mapping using the Task 130 session-status boundary

- Bouw een kleine vervolgslice op Task 130: account-mode verification status mapping via de bestaande session-status boundary.
- Blijf disabled-by-default en read-only; gebruik alleen fake-adapter tests voor varianten.
- Geen auto-connect, geen account/portfolio sync, geen market-data runtime.

## Boundaries (locked)
- Geen suggesties.
- Geen action drafts.
- Geen Decision Packages runtime.
- Geen orders (submit/modify/cancel/bind).
- Geen broker execution.
- Geen fake brokerdata.
- Geen credentials in logs/API.

## CI and merge discipline
- Volg `docs/product/codex-red-green-ci-workflow.md`.
- Alleen handmatige merge na groene CI op alle zes jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
