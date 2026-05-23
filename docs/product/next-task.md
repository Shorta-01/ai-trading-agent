# Task 138 — Harden IBKR read-only adapter contracts and fake-adapter sync fixtures for cash, positions, open orders and executions.

## Goal
Versterk de Milestone B read-only sync contractbasis vóór echte TWS/Gateway runtime door adaptercontracten, foutclassificatie en deterministische fake fixtures in één milestone-sized, green-CI-first batch te hardenen.

## Files/docs to read before changes
- `AGENTS.md`
- `docs/product/current-state.md`
- `docs/product/project-handover.md`
- `docs/product/locked-decisions.md`
- `docs/product/version-1-backlog.md`
- `docs/product/version-1-scope-register.md`
- `docs/product/task-history.md`
- `docs/product/milestone-b-next-implementation-slices-task-137.md`
- `docs/product/ibkr-read-only-sync-foundation-batch-selection-task-132b.md`
- `docs/product/milestone-b-ibkr-read-only-runtime-slice-selection-task-129.md`
- `docs/product/codex-ci-quality-rules.md`
- `docs/product/codex-red-green-ci-workflow.md`

## Scope
1. Harden read-only adapter contracts for IBKR sync payloads of cash, positions, open orders and executions.
2. Add/upgrade deterministic fake-adapter fixtures for these payload families.
3. Add explicit error-category handling/tests that separate:
   - adapter/runtime access failures;
   - payload validation failures.
4. Keep changes bounded to contract/validation/testable read-only behavior; no real network runtime.

## Non-goals
- Geen echte TWS/Gateway network adapter runtime.
- Geen persistent worker-managed IBKR session manager.
- Geen market-data runtime of FX runtime.
- Geen API/web featureverbreding buiten contractveiligheid.
- Geen storage schemawijzigingen of Alembic migraties.
- Geen suggesties, action drafts, orders, broker execution of live trading.

## Required tests
- Gerichte unit/contracttests voor adaptercontracten en fake fixtures (cash/positions/open orders/executions).
- Regressietests voor error-classificatie adapter failure vs payload validation failure.
- Bestaande relevante package tests voor gewijzigde modules.

## Required product tracking updates
- `docs/product/current-state.md`
- `docs/product/project-handover.md`
- `docs/product/task-history.md`
- `docs/product/version-1-backlog.md`
- `docs/product/version-1-scope-register.md`
- `docs/product/next-task.md` (doorzetten naar volgende taak na afronding)

## Required local checks
- `python -m py_compile scripts/check_product_tracking.py scripts/project_status.py`
- `python scripts/check_product_tracking.py`
- `python scripts/project_status.py`
- plus impacted lint/type/test commands for modified code packages.

## CI rules
- Do not merge until all required GitHub CI jobs are green: `domain`, `storage`, `portfolio`, `api`, `worker`, `web`.
- Latest CI run must be after the latest commit.
- If CI fails, fix in same PR branch; no repair PR split.

## Safety boundaries
- Version 1 remains paper-only.
- AI remains explanation/research-only; no execution authority.
- No broker execution path may be added or widened.
- No hidden data correction; validation outcomes must remain explicit and auditable.
