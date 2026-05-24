# Task 162

Slice 7 — User-approved IBKR paper submission with the locked
state-machine handshake. Add an editable-draft API surface
(`PATCH /action-drafts/{id}`) that re-runs sizing + dry-run, a separate
final-confirmation endpoint (`POST /action-drafts/{id}/approve`) that
re-validates everything one last time and persists an `approval_status`,
then a single submission endpoint
(`POST /action-drafts/{id}/submit-to-ibkr-paper`) gated **only** on a
dry-run-passed + approved + paper-mode draft. Real `ibapi` order
submission for LMT/DAY/whole shares only, tracked through the state
machine `Draft → Safety checked → User approved → Submitted → Awaiting
IBKR reply → Reply confirmed → Working → Filled/Cancelled/Rejected →
Reconciled`. Disabled-by-default; paper account only; no auto-submission;
critical alerts on every state transition.
