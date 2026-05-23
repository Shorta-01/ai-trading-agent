# Task 136 — Continue Milestone B conservatively after Task 135B-R with one scoped, green-CI-first slice from the existing backlog (no repair work planned).

## Guardrails
- Start only after the current repair PR is merged and all six CI jobs are green (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
- Keep Version 1 paper-only and read-only safety boundaries unchanged.
- No live trading, broker execution, suggestions, action drafts, or orders.
