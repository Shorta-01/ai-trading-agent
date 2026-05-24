# Task 168

Slice 13 — Deployment hardening + V1 release readiness. With every
critical-path slice now in place (IBKR sync, market data, forecasts,
suggestions, Decision Packages, action drafts, paper submission,
reconciliation + Prediction Diary, Research Desk, AI explanation,
Belgian tax, daily briefing), the next slice tightens the deployment
posture before V1 cut-over.

Scope:
- Storage migration adding a single `release_readiness_audits` table
  (one row per audit run) capturing the deterministic readiness
  scorecard: which feature flags are enabled, which providers are
  configured, which safety boolean defaults are still hard-False, the
  Alembic head, and the audit's Dutch summary.
- Pure-Python `release_readiness` module in `packages/portfolio` that
  takes the typed inputs and returns a deterministic readiness scorecard
  + Dutch summary. AI is not invoked.
- New route `POST /release/readiness/audit` and `GET /release/readiness/latest`.
- Web "Release readiness" panel summarising the scorecard.

Disabled-by-default; safety booleans hard-False; no broker action.
