# Task 188

Slice 33 — V1.1 UX upgrade. Surfaces the V1.1 internals on the
Portefeuille via three new web panels + a Dutch-microcopy review.

Scope:
- New **Predictor leaderboard** panel (apps/web) consuming
  `GET /predictor/backtest/latest` + `GET /predictor/leaderboard`.
  Shows each predictor's latest Brier-score, hit-rate,
  Sharpe-ratio + the auto-weight under the V1.1 §22.5 strategy.
- New **Backtest history** panel showing the most-recent N backtest
  rows per (model_code, asset_symbol) so the operator can see the
  trend after a settings change.
- New **Decision Package diff** view comparing the most recent
  Decision Package against the previous morning's version per
  symbol. Highlights changed `prob_gain`, action label, and the
  research-evidence list.
- New **Universe set chooser** in the Portefeuille header,
  reading `GET /universe/registry` and writing to the
  `universe_set` setting (a future widening; in this slice the
  chooser is read-only, surfacing the configured set + the
  available set list for the operator to put in their env).
- New **Claude AI budget surface** in the existing AI usage card:
  current month's running total, remaining headroom, and the cap.
- Dutch-microcopy review across the Portefeuille panels (action
  labels, action-draft state machine labels, briefing summary
  text, dry-run failure-code translations).

Backend additions (only what the UX surface needs):
- `GET /predictor/backtest/history?model_code=&asset_symbol=&limit=20`
  returns the last N rows for the trend chart.
- `GET /claude/budget/status` returns
  `{budget_month, monthly_cap_eur, monthly_total_eur,
    remaining_eur, exceeded}` using the existing
  `claude_ai_budget.monthly_budget_status(...)`.
- `GET /decision-packages/{conid}/diff` compares the most recent
  two Decision Packages for a conid; returns the JSON diff +
  per-field change list.

Tests cover: each new route's blocked / not-found / ok paths;
the existing apps/api 671 tests still pass; the apps/web Vitest
suite covers the new panels' rendering.

Manual approval gate stays; safety booleans hard-False on every
response.

When Slice 33 ships, Slice 34 (V1.1 release readiness) is
unblocked.
