# Next Task

## Task 108 — Conservatieve read-only implementatie-prep audit (non-runtime foundation preflight)

Doel:
- Voer een bounded documentatie/design preflight uit voor de eerstvolgende non-runtime foundation stap, met expliciete check tegen `docs/product/locked-decisions.md`.
- Bevestig dat read-only status, metadata/status-only en “geen runtime” terminologie consistent blijft terwijl implementatievoorbereiding wordt aangescherpt.

Niet doen in Task 108:
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
- Compacte preflight-notitie met expliciete verwijzing naar de terminology lock in `docs/product/locked-decisions.md` en bevestiging dat Task 107 tracking-drift preventieregel is nageleefd.
