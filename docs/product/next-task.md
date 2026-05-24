# Task 166

Slice 11 — Belgian tax module (TOB + 30% dividend roerende voorheffing).
The V1 product locks require deterministic Belgian tax projections on
every action draft Orderimpact and on every realised position.

Scope:
- Pure-Python `belgian_tax` module in `packages/portfolio` with
  `compute_tob(*, transaction_value, security_class) -> Decimal` (locked
  rates: 0.12% / 0.35% / 1.32% per asset class), and
  `compute_dividend_withholding(*, gross_dividend) -> Decimal` (locked
  30% rate).
- Extend `action_draft_safety.compute_orderimpact(...)` to surface the
  estimated TOB cost as a new `estimated_belgian_tob` field, threaded
  through to the persisted `AssetActionDraftRecord` (migration 0035).
- Surface the estimated TOB on the Action drafts table in the
  Portefeuille page.

Belgian-only tax math; no broker execution; no AI. The TOB is
*informational* on the draft — it doesn't change order sizing in V1.
