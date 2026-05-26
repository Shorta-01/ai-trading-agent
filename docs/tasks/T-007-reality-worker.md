```yaml
id: T-007
title: Write reality docs for the worker
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the three target files under `docs/reality/components/` do not exist (verified). The 37 worker source files (~8871 LoC excluding `__init__.py`) plus intent refs `docs/architecture.md` (157 lines) and `docs/decisions/0003-forecast-engine-architecture.md` are read in parallel by three subagents grouped per the task spec.
  - Agent A — orchestration & scheduling: `main`, `config`, `orchestrator`, `scheduler`, `single_flight_lock`, `storage_readiness`, `health`, `ibkr_gateway`, `starter_watchlist`, plus `docs/architecture.md` (intent).
  - Agent B — forecasting & decision-package: `forecasting/{asset_universe_resolver, calibration_step, forecasting_step, historical_bootstrap, label_translator}`, `decision_package/{composer, dutch_explanation_template, orchestration}`, `market_data_step`, `providers/eodhd`, plus `docs/decisions/0003-forecast-engine-architecture.md` (intent).
  - Agent C — actions & reconciliation: `action_draft/{composer, supersede_check}`, `ibkr_submission/{lifecycle_handler, order_builder, safety_recheck, submission_sweep, submitter}`, `ibkr_reconciliation/{pass_a_orphaned_executions, pass_b_stale_in_flight, pass_c_timeout_recovery, reconciler}`.
- **Step 2 (one-line per touched file):** three target files do not exist; each will hold one sub-cluster reality doc.
  - `worker-orchestration-and-scheduling.md` — entry point, settings, APScheduler job registration + cron + advisory-lock, the five `mode_detected` modes (cold-start / normal / disconnected / skipped_locked / market_closed), IBKR TWS gateway connect lifecycle, single-flight lock pattern, storage readiness probe, starter-watchlist seeding.
  - `worker-forecasting-and-decision-package.md` — universe resolver, calibration, walk-forward forecasting step, historical bootstrap math, label translator (8-bucket Dutch labels), `market_data_step` ingest, EODHD adapter, decision-package composer + hash-chain invariants + Dutch explanation template.
  - `worker-actions-and-reconciliation.md` — action-draft composer + supersede check, safety re-check (the final pre-`placeOrder` guard), order builder + submitter (sole `placeOrder` site in the project), lifecycle handler, submission sweep, three reconciliation passes (orphaned-executions / stale-in-flight / timeout-recovery), reconciler orchestrator.
- **Step 3 (one-line change):** write three cited reality docs covering the entire `apps/worker/src/portfolio_outlook_worker/` tree (37 files), no source modified.
- **Step 4 (criteria measurable):** yes — eight acceptance criteria: three output files exist; APScheduler job registration with cron + advisory-lock cited; 5 `mode_detected` enum modes cited; forecasting math entry points + label translator cited; decision-package hash-chain invariants cited; action-draft composer + safety re-check + submitter + lifecycle handler + sweep cited with the read-only safety boundary (only the worker has `placeOrder` authority); three reconciliation passes per-pass; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — API IBKR / forecasting / actions clusters (T-004, T-005) are out of scope; frontend (T-008) is out of scope.

## Goal

Produce three reality docs covering the entire worker source tree (`apps/worker/src/portfolio_outlook_worker/`).

## Context

The worker is the long-lived process: APScheduler + IBKR TWS session + forecasting + decision package + action draft composition + IBKR submission + reconciliation. 37 source files across six sub-packages. `depends_on:` —.

## Touch scope

Create:
- `docs/reality/components/worker-orchestration-and-scheduling.md`
- `docs/reality/components/worker-forecasting-and-decision-package.md`
- `docs/reality/components/worker-actions-and-reconciliation.md`

Read: all worker source files, plus existing intent docs `docs/architecture.md` and ADR 0003.

## Acceptance criteria

- [ ] Three output files at the locked filenames.
- [ ] APScheduler job registration documented in the orchestration file (cron expressions, job stores, advisory-lock pattern).
- [ ] Cold-start, normal, disconnected, skipped-locked, market-closed modes documented with the `mode_detected` enum cited.
- [ ] Forecasting math entry points + label translator documented in the forecasting file.
- [ ] Decision-package composer hash-chain invariants documented with refs.
- [ ] Action-draft composer + safety re-check + submitter + lifecycle handler + sweep documented in the actions file, with the read-only safety boundary cited (only the worker has placeOrder authority).
- [ ] Reconciliation Pass A / B / C documented per pass.
- [ ] No source modification.

## Out of scope

- API IBKR / forecasting / actions clusters (T-004, T-005).
- Frontend (T-008).

## Verification

- All three files exist.
- Module catalogues cover every `.py` file under `apps/worker/src/portfolio_outlook_worker/`.

## Notes

Sub-package groupings:
- `worker-orchestration-and-scheduling.md`: `main`, `config`, `orchestrator`, `scheduler`, `single_flight_lock`, `storage_readiness`, `health`, `ibkr_gateway`, `starter_watchlist`.
- `worker-forecasting-and-decision-package.md`: `forecasting/` (5 files), `decision_package/` (4 files), `market_data_step`, `providers/eodhd`.
- `worker-actions-and-reconciliation.md`: `action_draft/` (3 files), `ibkr_submission/` (6 files), `ibkr_reconciliation/` (5 files).
