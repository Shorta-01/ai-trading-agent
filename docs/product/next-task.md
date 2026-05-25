# Task 177

Slice 22 — V1 release readiness. The final slice of the V1
expansion queue. Brings the chain Slice 21 wired up to a state
where an operator can actually run V1 against a real paper
account.

Scope:
- Deterministic readiness scorecard helper that aggregates the
  per-leg `<x>_sync_enabled` flags, the IBKR session reachability,
  the EODHD key presence, the scheduler state, and the morning-
  chain default-legs return values into a single Dutch summary
  with a stable list of remaining blockers (e.g. `eodhd_not_configured`,
  `ibkr_session_not_reachable`, `scheduler_disabled`,
  `decision_packages_sync_disabled`).
- New route `GET /v1/release-readiness` returning the scorecard;
  no persisted state. Web: a small "V1 readiness" tile on the
  Portefeuille header.
- End-to-end acceptance test (pytest, stub providers) that runs
  the morning chain once with every leg enabled, asserts each
  leg returns `succeeded`, asserts the briefing alert list shape,
  and asserts no order leaves the manual approval gate.
- Documentation: env-var checklist (`.env.example` consolidated;
  highlight which env vars are required vs. optional), deployment
  notes (Docker / Compose layout), runbook stub for the daily
  morning-chain operator workflow.
- Lock the V1 expansion queue closed: `version-1-backlog.md` gains
  a "V1 complete" banner once this slice merges; the post-V1 widening
  ideas (full ~5 000-ticker universe, real TimesFM/Chronos clients,
  conditional orders, GTC/OPG, multi-account portfolios, mobile app)
  remain documented but explicitly out-of-scope.

No new persisted records; the readiness scorecard is computed
on-demand. Manual approval gate stays; safety booleans hard-False
everywhere.
