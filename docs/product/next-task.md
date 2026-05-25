# Task 174

Slice 19 — Fractional Kelly + risk-parity sizing. Locked in
`version-1-product-experience-locks.md §21.5`. Replaces the current
fixed-buy-value sizing in `action_draft_safety.derive_action_draft_sizing(...)`
with Kelly math driven by the ensemble's distribution.

Scope:
- New pure-Python `kelly_sizing` module in `packages/portfolio`:
  * `compute_fractional_kelly_fraction(*, prob_gain, expected_return_pct,
    downside_loss_pct, kelly_fraction=0.5)` returns the Kelly-recommended
    fraction of investable capital for one asset (always clipped to
    [0, 1]). Negative expected return → 0. Half-Kelly default.
  * `apply_risk_parity_caps(*, fraction, position_count,
    sector_exposure_pct, per_asset_cap_pct=5.0,
    per_sector_cap_pct=30.0)` clips an individual Kelly fraction so
    no single position exceeds 5% of the portfolio and no sector
    exceeds 30%.
- Extend `DraftSourceContext` with `prob_gain`, `expected_return_pct`,
  `downside_loss_pct`, `current_sector_exposure_pct`, and
  `current_portfolio_position_count` so the sizing function has
  enough to apply Kelly + risk-parity caps.
- Replace `derive_action_draft_sizing(...)` BUY math from
  ``floor(default_buy_value / market_price)`` to
  ``floor(kelly_fraction × usable_cash / market_price)``. Existing
  `Langzaam bijkopen` / `Verminderen` / `Verkopen` paths keep their
  current top-up/reduce semantics — Kelly only changes the BUY path.
- Wire the ensemble's `PredictionDistribution` (p50, prob_gain,
  expected_return_pct) into the `decision_package_sync` so the
  Decision Package carries the Kelly-derived sizing context. The
  Decision Package gains five new audit fields: `kelly_fraction`,
  `kelly_fraction_capped`, `kelly_per_asset_cap_hit`,
  `kelly_per_sector_cap_hit`, `kelly_explanation_nl`.
- Migration `0040_decision_package_kelly_fields` adds those fields to
  `asset_decision_packages` (nullable).
- Tests cover the Kelly math (every edge case), the risk-parity cap
  application, the sizing replacement on the BUY path, and the
  Decision Package serialisation surface.

No new routes; no broker action; safety booleans hard-False.
