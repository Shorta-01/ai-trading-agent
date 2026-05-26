# 0014 — Adopt the predictor-lifecycle architecture

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/predictor-lifecycle.md`, `docs/intent/forecast-engine.md`, `docs/intent/prediction-diary-and-calibration.md`, doctrine §13 and §15.

## Context

T-024 (`predictor-backtest-and-leaderboard.md` reality) needed to land:

1. The backtest methodology (walk-forward, look-ahead bias, transaction costs, survivorship, regime stratification).
2. The cadence of backtests (on-add, monthly, regime-triggered, on-demand).
3. The leaderboard's column set, drill-downs, sort options, time-window toggle, navigation pattern.
4. The path by which a new predictor enters the ensemble (and the symmetric path by which one leaves).

Without these locked, every future task touching predictors would re-derive a different answer.

## Decision

Adopt the architecture defined in `docs/intent/predictor-lifecycle.md`:

- **Walk-forward backtesting.** Rolling 12-month train / 1-month test / monthly step.
- **Look-ahead bias prevention.** Timestamp discipline via `published_at`; framework refuses data with `published_at > simulated_time`.
- **Transaction costs mandatory.** TOB + IBKR commission + half-spread (5bp liquid ETFs, 20bp less liquid stocks).
- **Survivorship correction: documented limitation in v1** with explicit caveat in every backtest report. Phase 4 evolution candidate.
- **Regime stratification: deferred to Phase 4** (depends on regime-detection capability).
- **Backtest cadences:** on-add (CI-enforced weak gate; tighten later); monthly scheduled; regime-triggered (Phase 4); on-demand from Category 5 settings.
- **Leaderboard: Option C.** Read-only, per-predictor metrics + drill-down + sortable columns + time-window toggle (default 6-month). Linked from prediction track record screen, not a separate top-level entry.
- **Four-stage entry path** for new predictors: backtest report → merge as shadow-mode → 3-month observation → user-decision promotion via system-decision item.
- **Lifecycle symmetry:** 3-month shadow → promotion; 6-month miscalibration → retirement. Faster to add than to remove; biased toward ensemble stability.

## Alternatives considered

- **In-sample backtesting only.** Rejected: indistinguishable from curve-fitting; trivially refuted by walk-forward.
- **Backtest without transaction costs.** Rejected: produces fantasy results that lose money on contact with the real market.
- **Automatic promotion on threshold.** Rejected: a hot streak isn't evidence; the user-decision pattern adds an explicit check.
- **Allow direct promotion / retirement from the leaderboard.** Rejected: keeps the leaderboard read-only and routes all consequential decisions through the actions area, consistent with the doctrine §10 system-decision pattern.

## Consequences

- T-024 reality describes existing predictor-backtest and leaderboard code against this intent.
- T-016b (prediction track record screen) is positioned as the parent screen; the leaderboard is a sub-screen linked from it.
- Shadow-promotion + retirement thresholds remain doctrine §15 open.
- Survivorship-bias data source remains doctrine §15 open.
