# Next Task

## Task 110 — Conservatieve storage/API contract skeleton voor request logs, provider/source metadata en freshness-audit records

Doel:
- Implementeer een veilige non-runtime skeleton op basis van Task 109 contractpreflight voor request logs, provider/source metadata en freshness-audit records.

In scope (nog steeds non-runtime):
- storage models/contracts voor de drie domeinen;
- Alembic migration alleen indien aantoonbaar nodig voor skeleton-opslag;
- repositoryfuncties voor create/read/list status- en auditrecords;
- read-only/status API exposure voor auditcontracten indien scherp afgebakend;
- storage/API tests met conservatieve blocked-defaults voor safety booleans.

Niet doen in Task 110:
- geen provider calls;
- geen market-data runtime of runtime-fetch;
- geen latest-price fetching;
- geen scheduler/background jobs;
- geen historical fetching;
- geen forecast runtime;
- geen AI runtime;
- geen suggesties;
- geen Decision Packages runtime;
- geen actiedrafts;
- geen IBKR connectie of orders;
- geen fake data.

Acceptatie:
- Contracts volgen Task 109 veld-/status-/reason-code preflight.
- Safety booleans defaulten conservatief op blocked/false tot gates bestaan.
- `git diff --check` groen en relevante storage/API checks groen.
