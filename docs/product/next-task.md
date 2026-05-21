# Next Task

## Task 102 — Conservatieve read-only wording drift check in nieuwe productupdates

Doel:
- Beperk scope tot documentatie/review-hardening: verifieer bij nieuw toegevoegde productteksten dat de vergrendelde read-only terminology uit Task 101 intact blijft.
- Voeg alleen kleine tracking-updates toe waar wording-drift kan ontstaan.

Niet doen in Task 102:
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
