# Next Task

## Task 109 — Conservatieve storage/API contract preflight voor request logs, provider/source metadata en freshness-audit records

Doel:
- Definieer één scherpe non-runtime contractbasis voor drie foundationdomeinen:
  - request-log structuur (pacing/context/audit);
  - provider/source metadata-structuur;
  - freshness-audit recordstructuur.
- Leg expliciet vast welke velden/statussen later runtime-implementatie veilig moeten ondersteunen, zonder runtime nu te starten.

In scope (documentation/design-only):
- Nieuw preflightdocument met:
  - candidate field catalog;
  - minimale required vs optional contractvelden;
  - status/reason-code voorstel voor freshness-audit;
  - audit-linking en traceability voorstel;
  - dependency mapping naar bestaande read-only readiness contracten.
- Producttrackingupdates in dezelfde PR.

Niet doen in Task 109:
- geen market-data runtime of runtime-fetch;
- geen latest-price fetching;
- geen scheduler/background jobs;
- geen historical fetching;
- geen forecast runtime;
- geen AI runtime;
- geen suggesties/Decision Packages runtime/actiedrafts/orders;
- geen IBKR connectie/orderflow;
- geen fake data;
- geen code/migration/API-runtimewijzigingen.

Acceptatie:
- Documentatie-only diff onder `docs/product/`.
- Expliciete read-only terminology lock check tegen `docs/product/locked-decisions.md`.
- Expliciete bevestiging dat geen runtime unlock plaatsvond.
- `git diff --check` is groen.
