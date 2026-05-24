# Task 161

Slice 6 — Action draft skeleton + dry-run + `Orderimpact`. Generate an
editable, structured action-draft record (asset/conid/symbol/exchange/
currency/action/quantity/order_type=LMT/limit_price/tif=DAY/account_mode)
from a ready Decision Package, run a dry-run that recomputes safety
checks (usable cash ≥ buy value, sell quantity ≤ held, FX freshness,
market freshness, account-mode match), and surface a Dutch
`Orderimpact` panel showing cash before/after, position size after,
weight after, concentration impact. Persist to a new `asset_action_drafts`
table. **Still no submission to IBKR** — that's Slice 7. Disabled-by-default;
no order submission, no broker action.
