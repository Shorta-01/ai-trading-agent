# Task 137 — Milestone B planning slice after Task 136 (documentation-only selection).

- Doel: na Task 136 contract-uitlijning één conservatieve, green-CI-first implementatieslice selecteren vanuit de bestaande Milestone B backlog.
- Scope: planning/documentatie-only selectie met expliciete safety/non-goals; geen runtimewijzigingen.
- Guardrails: geen storage schema/migraties, geen echte TWS/Gateway runtime, geen market-data runtime, geen suggesties/action drafts/orders/broker execution.

## Guardrails
- Start only after the current repair PR is merged and all six CI jobs are green (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
- Keep Version 1 paper-only and read-only safety boundaries unchanged.
- No live trading, broker execution, suggestions, action drafts, or orders.
