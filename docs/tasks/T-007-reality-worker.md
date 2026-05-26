```yaml
id: T-007
title: Write reality docs for the worker
phase: P1
status: locked
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

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
