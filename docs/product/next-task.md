# Task 163

Slice 8 — Reconciliation + Prediction Diary. Pull the
`AWAITING_IBKR_REPLY`/`WORKING` submissions and reconcile them against
the IBKR sync open-orders + executions snapshots: transition states to
`FILLED` / `CANCELLED` / `REJECTED` and then `RECONCILED`, capturing
`filled_quantity` + `average_fill_price`. Write a Prediction Diary row
per suggestion (issued forecast vs realised outcome at 1d/1w/1m). New
routes `POST /action-drafts/reconcile`, `GET /prediction-diary`. Critical
alerts on state transitions and on stale approved drafts. Disabled-by-default;
no auto-submission; no AI scoring.
