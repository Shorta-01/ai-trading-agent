```yaml
id: T-017
title: Write reality doc for Decision Package composition flow
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/462
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/decision-package-composition.md` does not exist (verified). T-017 is a focused synthesis — every code site is cited in T-007 `worker-forecasting-and-decision-package.md` §§9-11 (DP composer + Dutch template + orchestration) + T-002 `portfolio-money-and-accounting.md` (Decimal discipline) + T-005 `api-actions-suggestions-and-watchlists.md` (Decision Package API surface). No new files read.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the per-asset Decision Package composition workflow doc.
  - `decision-package-composition.md` — trigger gate → orchestration iteration → per-asset compose → 5 locked gates → SHA-256 content-addressed hash + previous_package_hash chain → deterministic Dutch explanation template (no AI) → `decision_packages` row.
- **Step 3 (one-line change):** write one cited workflow reality doc tracing the per-asset DP composition flow.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; trigger gate documented (orchestrator step 10); 5 locked gate sequence documented with order rationale; hash-chain invariants documented (excluded fields + chain anchor); deterministic Dutch template documented (no AI); hard order-safety floor documented (`safe_for_action_drafts=False, safe_for_orders=False`); no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — forecast generation (T-015), AI explanation (T-023), action-draft composition (T-018), backtest (T-024).

## Goal

Produce one workflow reality doc tracing the per-asset Decision Package composition flow — from the orchestrator's step-10 gate firing at 07:00 morning_briefing → `compose_and_persist_for_run` orchestration iteration → per-asset `compose_decision_package` pure function with 5 locked gates → SHA-256 content-addressed hash chain → deterministic Dutch explanation template → persisted `decision_packages` row with hard order-safety floor.

## Context

`depends_on:` T-002, T-007. The Decision Package is the **immutable evidence-bundle** that justifies any future action draft. T-007 §§9-11 documented the composer at module level; T-017 zooms into the per-asset transformation and clarifies the hash-chain + idempotency story.

## Touch scope

Create:
- `docs/reality/workflows/decision-package-composition.md`

Read: T-002 + T-007 + T-005 reality docs (already on disk).

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] Trigger gate documented (orchestrator step 10: `forecast_details["error"]` absent + `mode_detected="normal"` + `run_type="morning_briefing"`).
- [ ] 5 locked gate sequence documented: `forecast_valid`, `data_fresh`, `asset_listing_resolved`, `freshness_within_sla`, `confidence_at_least_medium` — with the order rationale.
- [ ] Hash-chain invariants documented (composed_at + decision_package_id excluded from hash; previous_package_hash chain anchor).
- [ ] Deterministic Dutch template documented (no AI; 7-sentence locked structure).
- [ ] Hard order-safety floor (`safe_for_action_drafts=False, safe_for_orders=False`) + idempotency gap (UUID per write).
- [ ] No source modification.

## Out of scope

- Forecast generation (T-015 produces the rows this flow consumes).
- AI explanation (T-023 future).
- Action-draft composition (T-018 future).
- Backtest leaderboard (T-024).

## Verification

- File exists.
- All 5 gates cited with `composer.py:NN` anchors.
- The "deliberately excluded from hash" pair (composed_at, decision_package_id) cited.
- 6-label vocabulary cross-referenced (Geblokkeerd skip).

## Notes

The Decision Package is the **canonical evidence-bundle anchor** for the project's audit trail (AGENTS.md §20 — "Every decision must be logged"). Its content-addressed hash is the cryptographic backbone — two runs over the same inputs produce identical hashes despite fresh UUIDs. T-017 documents the why + the gap (intent: one row per `(decision_package_id, content_hash)` tuple; reality: fresh UUID per write, dedup left to consumers).
