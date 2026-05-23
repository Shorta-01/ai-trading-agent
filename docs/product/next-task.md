# Task 135B — Harden IBKR read-only sync adapter payload validation for cash, positions, open orders and executions after Task 134B execution gating, without real TWS/Gateway network runtime, without market-data runtime, without suggestions, without action drafts and without orders.


## Safe restart point after Task 135A audit
- Start from `main` at the first commit after merged PR #326 (Task 134B-R2), with no local/uncommitted Task 135B worktree changes.
- Use the reconciled tracking documents from Task 135A as source-of-truth before implementation (`current-state`, `project-handover`, `task-queue`, `version-1-backlog`, `version-1-scope-register`, `task-history`).
- Keep scope hard-limited to read-only payload validation hardening only; no real TWS/Gateway runtime, no market-data runtime, no suggestions, no action drafts, no orders.
