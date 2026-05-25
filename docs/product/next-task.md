# Task 189

Slice 34 — V1.1 release readiness. The final slice of the V1.1
expansion queue. Mirrors Slice 22's V1 release-readiness pattern
extended to cover the V1.1 §22 surface.

Scope:
- Extend the `release_readiness` module with V1.1-specific
  blocker codes:
  - `ensemble_weight_strategy_invalid` (must be `equal_weight`
    or `auto`)
  - `predictor_backtest_disabled`
  - `claude_ai_api_key_missing_when_real_client_enabled`
  - `claude_ai_budget_exceeded` (live check via the
    `claude_ai_budget_usage` audit table)
  - `universe_set_unknown` (when `UNIVERSE_SET` outside the
    locked set)
- Extend the `compute_release_readiness(settings, *, budget_repo)`
  helper so the budget-exceeded gate runs when storage is
  reachable; existing callers stay backward-compatible (the
  budget gate is skipped when `budget_repo=None`).
- Update the `GET /v1/release-readiness` route to thread the
  budget repo through; the scorecard now reports the V1.1
  gates alongside the V1 ones.
- New V1.1 end-to-end acceptance test (`test_v1_1_acceptance.py`)
  that runs the morning chain with every per-leg flag on AND
  the V1.1 rebuild knobs on (e.g.
  `momentum_horizon_scaled_thresholds=True`,
  `qvm_sector_neutral_zscore=True`,
  `ensemble_weight_strategy="auto"`) and asserts the chain
  still passes + the readiness scorecard reports `status="ready"`.
- Documentation:
  - Add a "V1.1 release readiness" section to
    `docs/deployment.md` mirroring the V1 runbook + listing the
    new env vars (the §22.2 budget cap, the universe-set
    chooser, the AI provider keys, the rebuild knobs).
  - Lock the V1.1 expansion queue closed: amend
    `version-1-1-backlog.md` with a "V1.1 is feature-complete"
    banner.
- `next-task.md` after this slice points at "V1.1 complete —
  fresh scope discussion needed for V1.2".

No new persisted records; no migration. Manual approval gate
stays; safety booleans hard-False everywhere.

When Slice 34 ships, the V1.1 expansion queue (Slices 23–34)
closes.
