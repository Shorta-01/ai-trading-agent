# Task 187

Slice 32 — V1.1 conditional orders + GTC/OPG/IOC TIF. Extends the
V1 §21.3 order vocabulary with the full IBKR conditional set per
the §22.3 lock.

Scope:
- Extend `LOCKED_ORDER_TYPES` with `CONDITIONAL`. The
  conditional order carries a parent base type (LMT / MKT /
  STP / STP_LMT) plus a list of activation conditions.
- Extend the locked TIF set from `DAY`-only to
  `{DAY, GTC, OPG, IOC}`.
- New `OrderCondition` dataclass family — one variant per IBKR
  condition kind:
  - `PriceCondition(symbol, conid, exchange, operator, trigger_price)`
  - `TimeCondition(operator, trigger_at_utc)`
  - `MarginCondition(operator, percent)`
  - `VolumeCondition(symbol, conid, operator, volume)`
  - `ExecutionCondition(symbol, sec_type, exchange)`
- Storage migration `0044_action_draft_conditional_orders`
  adds a child table `action_draft_order_conditions` keyed on
  `(draft_id, condition_index)` with the union of fields needed
  to reconstruct any one of the five condition kinds.
- `AssetActionDraftRecord.tif` constraint widens to
  `{DAY, GTC, OPG, IOC}`; `__post_init__` rejects anything
  outside the set. Existing rows stay at `DAY`.
- Dry-run safety codes for the new vocabulary:
  - `conditional_missing_parent_order_type`
  - `conditional_no_conditions_listed`
  - `conditional_unknown_condition_kind`
  - `conditional_price_missing_trigger`
  - `conditional_time_missing_trigger`
  - `conditional_margin_invalid_percent`
  - `tif_gtc_requires_real_account` (paper accounts may not
    honour GTC the same way)
- IBKR submission client extends `OrderSubmissionInputs` with
  optional `conditions: list[OrderCondition]` and `tif`; the
  `build_contract_and_orders(...)` helper maps each condition
  kind to ibapi's `Order.conditions` API.
- Tests cover: dataclass invariants per condition kind, dry-run
  safety codes, ibapi conditions wiring per kind, TIF widening
  on the record, backwards-compat for existing LMT/DAY orders.

Manual approval gate stays; safety booleans hard-False on every
persisted record.

When Slice 32 ships, Slice 33 (UX upgrade) is unblocked.
