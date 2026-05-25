# Task 175

Slice 20 — Full IBKR order vocabulary. Extends action drafts to the
full set of IBKR order types locked in
`version-1-product-experience-locks.md §21.3`.

Scope:
- Storage migration `0040_action_draft_order_vocabulary` extends
  `asset_action_drafts` with:
  * `order_type` constraint widened from "LMT only" to the locked
    set `{LMT, MKT, STP, STP_LMT, TRAIL, TRAIL_LMT, BRACKET}`
  * new columns: `stop_price`, `trail_amount`, `trail_percent`,
    `bracket_take_profit_limit_price`, `bracket_stop_loss_price`
    (all nullable Decimal)
- Extend `AssetActionDraftRecord` with the new fields + per-type
  invariants in `__post_init__`:
  * LMT requires `limit_price`; STP requires `stop_price`; STP_LMT
    requires both; TRAIL requires `trail_amount` XOR
    `trail_percent`; TRAIL_LMT same + `limit_price`; BRACKET
    requires `limit_price` + `bracket_take_profit_limit_price` +
    `bracket_stop_loss_price`; MKT requires none.
- Extend `action_draft_safety.run_dry_run_safety_checks(...)` with
  per-order-type validation. Failures use stable codes
  (`stp_missing_stop_price`, `trail_amount_and_percent_set`, etc.).
- Real submission client (`IbapiOrderSubmissionClient`) gains a
  mapping from the locked order-type set to ibapi's `Order` flags
  (`orderType="MKT|LMT|STP|STP LMT|TRAIL|TRAIL LIMIT"`, auxPrice,
  trailingPercent, etc.). For BRACKET: emit the parent + take-profit
  + stop-loss as a 3-order group.
- Approval orchestrator + state machine unchanged — the per-draft
  user approval gate stays.
- Tests cover record invariants per type, dry-run failure codes, and
  the submission client's mapping for each order type.

No new routes; no UI change in this slice; manual approval gate stays.
