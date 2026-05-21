# Next Task

## Task 107 — Conservatieve read-only terminology lock sustainability mini-check

Doel:
- Houd scope documentatie-only en voer een korte sustainability-check uit op producttracking na Task 106.
- Bevestig dat `docs/product/locked-decisions.md` leidend blijft voor read-only status, metadata/status-only en expliciete “geen runtime” formuleringen.

Niet doen in Task 107:
- geen market-data runtime of runtime-fetch;
- geen latest-price fetching;
- geen scheduler/background jobs;
- geen forecast runtime;
- geen AI runtime;
- geen suggesties/Decision Packages/actiedrafts/orders;
- geen fake data;
- geen API/web/storage runtimewijzigingen.

Acceptatie:
- Documentatie-only diff.
- Gerichte cross-doc consistencycheck met expliciete lock-verwijzing naar `docs/product/locked-decisions.md`.
