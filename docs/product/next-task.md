# Next Task

## Task 104 — Conservatieve read-only tracking consistency mini-follow-up

Doel:
- Houd scope documentatie-only en verifieer dat Task 103 trackingupdates consistent blijven met de vergrendelde read-only terminology uit `docs/product/locked-decisions.md`.
- Corrigeer alleen kleine tracking- of wordingdrift die review kan misleiden.

Niet doen in Task 104:
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
- Conservatieve cross-doc consistentiecheck met expliciete referentie naar `docs/product/locked-decisions.md`.
