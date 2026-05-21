# Next Task

## Task 103 — Conservatieve read-only product-doc consistency follow-up

Doel:
- Houd scope documentatie-only en bevestig dat nieuwe productupdates de vergrendelde read-only terminology uit `docs/product/locked-decisions.md` blijven volgen.
- Werk alleen kleine tracking- of wordingdrift bij als die reviewers kan misleiden.

Niet doen in Task 103:
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
- Cross-doc consistentie bevestigd met verwijzing naar `docs/product/locked-decisions.md` terminology lock.
