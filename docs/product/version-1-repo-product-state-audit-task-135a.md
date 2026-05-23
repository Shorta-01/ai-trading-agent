# Task 135A — Version 1 repository/product state audit and reconciliation

## Purpose
Task 135A reconciles product tracking documentation with repository truth on `main` after merged PR #326 (Task 134B-R2).

## Repo and CI state
- Latest verified merged PR baseline for this audit: PR #326 (Task 134B-R2).
- Latest verified CI baseline: run #653 green across six required jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
- Open PRs at audit start: none verified.

## Product tracking state reconciled
- `current-state.md` marker corrected to `Huidige toestand: **na Task 134B-R2**`.
- `task-queue.md` Milestone B stale wording corrected from “Task 133B next” to completed chain 133B → 134B → 134B-R/134B-R2 and 135B next.
- `version-1-backlog.md` Next up section clarified: Task 135B remains next implementation task.
- `project-handover.md`, `task-history.md`, `version-1-scope-register.md` updated with Task 135A documentation-only completion.
- `next-task.md` remains Task 135B and now includes explicit safe restart point.

## Completed or verified foundations on `main`
- Repository skeleton and six-job CI foundation: present.
- Storage/migration readiness foundations: present from prior tasks.
- Research Source Archive storage/API/UI foundations: partial foundations present from prior tasks.
- Request logs/provider/freshness audit foundations: present from prior tasks.
- Asset master/listing/watchlist foundations: present (foundation-level).
- Market-data storage/readiness foundations: present without runtime fetch scheduler/provider runtime.
- FX snapshot storage/readiness foundations: present without runtime FX provider integration.
- IBKR read-only status/session boundary (Tasks 130/131B): present.
- IBKR read-only sync readiness/preflight gate (Task 133B): present.
- Manual sync execution blocking (Task 134B): present.
- Task 134B-R and 134B-R2 repairs: present/merged.
- Durable IBKR sync snapshot storage for sync runs/cash/positions/open orders/executions: present as storage/read-model foundation.
- Portfolio valuation readiness foundation using stored snapshots: present (readiness/display foundation).
- Web dashboard/readiness display foundations: present in foundation/readiness form.

## Foundation-only / not full runtime
- IBKR real TWS/Gateway network runtime: not started (blocked by scope).
- Persistent IBKR session manager: not full runtime.
- Real account/portfolio sync runtime: not started as real runtime.
- Market-data runtime/scheduler/provider integration: not started as full runtime.
- Research Library full extraction/scoring/runtime: not started as full runtime.
- Prompt-injection engine: not started.
- Source credibility engine: not started.
- Evidence Ledger runtime/API/UI: not started as full runtime.
- Decision Packages runtime: not started.
- Suggestion engine: not started.
- Action drafts: not started.
- Broker submission/user-approved order flow: not started.
- Alerts/daily briefing/Prediction Diary runtime: not started.
- Deployment/backup/restore readiness: not completed.

## Confirmed next task recommendation
Task 135B remains the correct next implementation task.

## Exact safe starting point for next Codex task
1. Start from clean `main` aligned with merged PR #326 baseline (no local/uncommitted Task 135B leftovers).
2. Read reconciled tracking docs first: `project-handover.md`, `current-state.md`, `version-1-backlog.md`, `task-queue.md`, `next-task.md`, `version-1-scope-register.md`, `task-history.md`.
3. Execute Task 135B only within locked scope: harden read-only IBKR sync adapter payload validation for cash/positions/open orders/executions.
4. Keep hard exclusions: no real TWS/Gateway runtime, no market-data runtime, no suggestions, no action drafts, no orders/live trading.
