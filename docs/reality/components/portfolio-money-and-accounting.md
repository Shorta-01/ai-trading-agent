# `packages/portfolio` — money and accounting

**Phase:** 1a (reality components)
**Task:** T-002
**Scope:** nine modules in `packages/portfolio/src/portfolio_outlook_portfolio/` that form the package's money / valuation / lot / ledger layer. They sit above `packages/domain` primitives and below the predictors, guards, and briefing.

This file is descriptive. It states what the code at HEAD does today, with `path/to/file.py:NNN` citations and short excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `money.py` — currency-consistency primitives.
- `accounting.py` — gross / net / cash-delta calculators.
- `lots.py` — lot-status derivation and pro-rata cost-basis allocation.
- `snapshot.py` — paper-portfolio snapshot composition (cash + positions + transaction totals).
- `performance.py` — cash-flow, cost/tax, total-value, return-since-start.
- `valuation_conversion_totals.py` — multi-currency conversion totals with status-rich result.
- `valuation_cost_basis_pl.py` — per-position cost basis + unrealized P&L (no FX inside).
- `term_deposits.py` — term-deposit projections (simple interest, EOM-clamped dates).
- `ledger_services.py` — ledger-entry constructors + transaction/cash-entry pair invariants.

## `money.py` — currency-consistency primitives

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/money.py`

### Public surface

- `ensure_same_currency(*amounts: Money) -> CurrencyCode` — variadic; rejects empty input and any currency mismatch.
- `add_money(amounts: Sequence[Money]) -> Money` — requires non-empty sequence, all-same-currency; seeds running sum with `Decimal("0")` (`money.py:25`).
- `subtract_money(left: Money, right: Money) -> Money` — same-currency only; negative results allowed (no sign guard).
- `multiply_quantity_by_price(quantity, price) -> Money` — refuses `quantity <= 0`; allows `price == 0`.

### Collaborators

`portfolio_outlook_domain` primitives (`CurrencyCode`, `Money`, `Quantity`) and `.errors` only. Lowest layer in the package; everything else builds on it.

### Notable choices

- All arithmetic uses `Decimal`; no rounding is performed inside this module.
- `multiply_quantity_by_price` enforces strict-positive quantity but zero-or-positive price — asymmetric on purpose (`money.py:35-38`).

```python
# money.py:20-26
def add_money(amounts: Sequence[Money]) -> Money:
    if not amounts:
        raise InvalidAccountingInputError("add_money requires at least one Money value.")

    currency = ensure_same_currency(*amounts)
    total = sum((amount.amount for amount in amounts), start=Decimal("0"))
    return Money(amount=total, currency=currency)
```

## `accounting.py` — gross / net / cash-delta calculators

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/accounting.py`

### Public surface

- `calculate_gross_amount(quantity, price)` — alias for `multiply_quantity_by_price`.
- `calculate_total_costs(costs, currency)` — sums cost-estimate Decimals; returns `Money(0, currency)` on empty.
- `calculate_net_transaction_amount(side, gross_amount, costs)` — BUY adds, SELL subtracts.
- `calculate_cash_delta_for_transaction(side, net_amount)` — negates on BUY, keeps positive on SELL.
- `validate_transaction_amounts(transaction: PaperTransaction) -> None` — re-derives gross/net from the transaction and raises on mismatch via `==` (rounding-sensitive) (`accounting.py:64-77`).

### Collaborators

`.money` (`add_money`, `ensure_same_currency`, `multiply_quantity_by_price`), `.errors`, `portfolio_outlook_domain` (`CostEstimate`, `CurrencyCode`, `Money`, `PaperTransaction`, `Quantity`, `TransactionSide`).

### Notable choices

- Costs are positive `Money`; sign is applied by `side`. Unrecognised side raises `InvalidAccountingInputError` (`accounting.py:49`).
- `calculate_total_costs` is the FX-boundary check for costs vs. transaction currency (`accounting.py:26-28`).

```python
# accounting.py:33-49
def calculate_net_transaction_amount(
    side: TransactionSide,
    gross_amount: Money,
    costs: Sequence[CostEstimate],
) -> Money:
    total_costs = calculate_total_costs(costs, gross_amount.currency)
    if side is TransactionSide.BUY:
        return Money(amount=gross_amount.amount + total_costs.amount, currency=gross_amount.currency)
    if side is TransactionSide.SELL:
        return Money(amount=gross_amount.amount - total_costs.amount, currency=gross_amount.currency)
    raise InvalidAccountingInputError(f"Unsupported transaction side: {side}")
```

## `lots.py` — lot-status derivation and pro-rata cost basis

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/lots.py`

### Public surface

- `calculate_remaining_quantity(original, allocated)` — raises `InsufficientLotQuantityError` if `allocated > original`.
- `derive_lot_status(original, remaining)` — pure derivation: OPEN if equal, CLOSED if remaining exactly zero, else PARTIALLY_CLOSED.
- `validate_lot_quantities(lot)` — checks quantity invariant and status consistency.
- `calculate_allocated_cost_basis(lot, allocated_quantity)` — pro-rates by `allocated / original` (`lots.py:43-46`).

### Collaborators

`.errors`, `portfolio_outlook_domain` (`LotStatus`, `Money`, `PaperLot`, `Quantity`). Notably **does not depend on `money.py`**.

### Notable choices

- Cost-basis allocation divides by `lot.original_quantity` (not `remaining`), so each unit retains its original per-unit cost. Result is unrounded `Decimal`; precision drift is possible.
- `derive_lot_status` uses strict `==` on `Decimal`; trailing-zero scale (e.g. `Decimal("0.00") == Decimal("0")`) does not affect classification.

```python
# lots.py:16-23
def derive_lot_status(original_quantity: Quantity, remaining_quantity: Quantity) -> LotStatus:
    if remaining_quantity.value > original_quantity.value:
        raise InvalidAccountingInputError("remaining_quantity cannot exceed original_quantity.")
    if remaining_quantity.value == original_quantity.value:
        return LotStatus.OPEN
    if remaining_quantity.value == Decimal("0"):
        return LotStatus.CLOSED
    return LotStatus.PARTIALLY_CLOSED
```

## `snapshot.py` — paper-portfolio snapshot composition

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/snapshot.py`

### Public surface

- Frozen dataclasses: `InstrumentPositionQuantity` (`:20`), `InstrumentTransactionTotals` (`:26`), `PaperPortfolioSnapshot` (`:35`).
- Private mutable accumulator `_TotalsBucket` (`:43`) — the only mutable struct in this group.
- Functions: `calculate_cash_balances(entries)` (`:53-58`); `calculate_position_quantities(transactions)` (`:61-93`); `calculate_transaction_totals(transactions)` (`:96-148`); `validate_no_oversells(transactions)` (`:151-170`); `build_paper_portfolio_snapshot(...)` (kw-only orchestrator).

### Collaborators

`.money` (`add_money`), `.errors`, `portfolio_outlook_domain` (`CashLedgerEntry`, `InstrumentId`, `Money`, `PaperTransaction`, `PortfolioId`, `Quantity`, `TransactionSide`, `TransactionStatus`).

### Notable choices

- Multi-currency cash is supported per-portfolio (`cash_balances: dict[str, Money]` keyed by currency).
- Transaction totals require **single currency per side per instrument** — mixing buy or sell currencies for one instrument raises `CurrencyMismatchError` (`snapshot.py:121-133`).
- Non-FILLED transactions silently skipped (`snapshot.py:67, :102`).
- Oversell detection runs **before** position aggregation so error messages can include chronological time (`snapshot.py:151-170`). Stable sort: `(occurred_at, original_index)`.

```python
# snapshot.py:151-170
def validate_no_oversells(transactions: Sequence[PaperTransaction]) -> None:
    filled = [tx for tx in transactions if tx.status is TransactionStatus.FILLED]
    ordered = sorted(enumerate(filled), key=lambda item: (item[1].occurred_at, item[0]))

    running: dict[str, Decimal] = {}
    for _, tx in ordered:
        instrument_id = tx.instrument_id
        current = running.get(instrument_id, Decimal("0"))
        if tx.side is TransactionSide.BUY:
            running[instrument_id] = current + tx.quantity.value
        elif tx.side is TransactionSide.SELL:
            next_value = current - tx.quantity.value
            if next_value < Decimal("0"):
                message = ("Oversell detected for instrument "
                          f"{instrument_id} at {tx.occurred_at.isoformat()}.")
                raise InvalidAccountingInputError(message)
```

## `performance.py` — cash flow, cost/tax, return-since-start

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/performance.py`

### Public surface

Frozen dataclasses `PortfolioCashFlowSummary` (`:20`), `PortfolioCostAndTaxSummary` (`:28`), `PortfolioPerformanceSummary` (`:35`). Functions (all kw-only): `calculate_cash_flow_summary`, `calculate_cost_and_tax_summary`, `calculate_current_total_value`, `calculate_result_since_start`, `calculate_net_result_since_start`, `calculate_return_since_start` (returns `Percentage | None`), `build_portfolio_performance_summary`.

### Collaborators

`.money` (`ensure_same_currency`), `.errors`, `portfolio_outlook_domain` (`CashLedgerEntry`, `CostEstimate`, `CostType`, `CurrencyCode`, `LedgerEntryType`, `Money`, `Percentage`, `PortfolioId`).

### Notable choices

- Single-currency pipeline: `ensure_same_currency` called at every aggregation site (`performance.py:65, :96, :105, :124, :138, :154, :170, :186`).
- Withdrawals are **normalised to positive magnitudes** via `abs(entry.amount.amount)` (`performance.py:69`) even though stored withdrawal entries carry a negative amount (see `ledger_services.validate_cash_entry_sign`). Same `abs()` applied to FEE / TAX_ESTIMATE entries (`:107-109`).
- `calculate_return_since_start` uses an **adjusted base** of `starting_capital + deposits - withdrawals` (`performance.py:171`). Returns `None` sentinel when adjusted base ≤ 0 (`performance.py:172-173`).
- No rounding — `Percentage.value` is the raw Decimal result of `(net_result / adjusted_base) * 100`.

```python
# performance.py:163-174
def calculate_return_since_start(
    *,
    net_result_since_start: Money,
    starting_capital: Money,
    deposits: Money,
    withdrawals: Money,
) -> Percentage | None:
    ensure_same_currency(net_result_since_start, starting_capital, deposits, withdrawals)
    adjusted_base = starting_capital.amount + deposits.amount - withdrawals.amount
    if adjusted_base <= Decimal("0"):
        return None
    return Percentage(value=(net_result_since_start.amount / adjusted_base) * Decimal("100"))
```

## `valuation_conversion_totals.py` — multi-currency conversion totals

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/valuation_conversion_totals.py` (350 lines)

### Public surface

Frozen dataclasses: `PositionConversionInput` (`:7`), `CashConversionInput` (`:15`), `FxPairConversionInput` (`:23`), `ValuationInputTrace` (`:34`), `ConversionTotalsInput` (`:44`), `ConversionTotalsResult` (`:53`). Type alias `ConversionStatus = str` (`:4`). Public function `calculate_conversion_totals(payload) -> ConversionTotalsResult` (`:120`). Hard-coded Dutch status text table `_STATUS_TEXT` (`:76-113`).

### Collaborators

**None in the portfolio package** — stdlib only (`dataclasses`, `decimal`). Does **not** use `Money` / `money.py` / `portfolio_outlook_domain` primitives; currencies are plain `str` and values are raw `Decimal`.

### Notable choices

- Status-rich result instead of raising. Nine status values (`conversion_ready`, `conversion_not_required`, six `conversion_blocked_*`, plus `conversion_control_needed_stale_fx`).
- Block precedence: incomplete inputs → missing market data → missing cash → missing base currency → invalid FX → stale FX → missing FX (`:136-227`). Stale FX yields a `*_control_needed_*` status; invalid blocks.
- Single-currency portfolios with no `base_currency` fall back to the only present currency (`:171-172`).
- FX pair string format `"{source}/{base}"` (`:267, :283, :300`).
- Uses bare `assert` for `None` checks inside summation helpers (`:278-279, :295-296`).

```python
# valuation_conversion_totals.py:179-203
for pair in required_pairs:
    fx = fx_by_pair.get(pair)
    if fx is None:
        missing_fx_pairs.append(pair)
        continue
    if fx.validation_status != "valid":
        invalid_fx_pairs.append(pair)
        continue
    if fx.freshness_status != "fresh":
        if fx.freshness_status == "stale":
            stale_fx_pairs.append(pair)
        else:
            invalid_fx_pairs.append(pair)
```

## `valuation_cost_basis_pl.py` — per-position cost basis + unrealized P&L

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/valuation_cost_basis_pl.py` (266 lines)

### Public surface

Frozen dataclasses: `PositionPlInput` (`:8`), `PositionPlInputTrace` (`:17`), `PositionPlCalculationInput` (`:25`), `PositionPlCalculationResult` (`:34`). Type alias `PlStatus = str` (`:5`). Public function `calculate_position_cost_basis_and_unrealized_pl(payload) -> PositionPlCalculationResult` (`:95`). Status-text table `_STATUS_TEXT` (`:58-88`) with eight Dutch-localised statuses.

### Collaborators

**None** — same dependency-free stance as `valuation_conversion_totals.py`. No `Money` / `Quantity` types; all numeric fields are raw `Decimal`.

### Notable choices

- Two independent statuses returned per call: `cost_basis_status` and `unrealized_pl_status` — allowing the cost basis to be ready while P&L is blocked on missing market value (`:204-233`).
- Short positions (negative quantity) explicitly rejected as out-of-scope: status `cost_basis_blocked_short_position` (`:124-131`).
- Formula: `cost_basis = quantity × average_cost_per_unit` (`:152`); `unrealized_pl = native_market_value − cost_basis` (`:163`); percentage only when `cost_basis > 0` (`:167-169`).
- Converted P&L computed only when both pre-converted values supplied — this module does **no** FX itself (`:171-175`).

```python
# valuation_cost_basis_pl.py:152-175
cost_basis = position.quantity * position.average_cost_per_unit

if position.native_market_value is None:
    missing_pl_inputs.append("native_market_value")
    return _cost_basis_ready_pl_blocked(...)

unrealized_pl = position.native_market_value - cost_basis

unrealized_pl_percent: Decimal | None = None
unrealized_pl_percent_available = False
if cost_basis > Decimal("0"):
    unrealized_pl_percent = unrealized_pl / cost_basis
    unrealized_pl_percent_available = True

converted_unrealized_pl_available = False
converted_unrealized_pl: Decimal | None = None
if payload.converted_market_value is not None and payload.converted_cost_basis is not None:
    converted_unrealized_pl = payload.converted_market_value - payload.converted_cost_basis
    converted_unrealized_pl_available = True
```

## `term_deposits.py` — term-deposit projections

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/term_deposits.py`

### Public surface

`term_months(term)` (`:20-27`); `calculate_maturity_date(start_date, term)` (`:30-36`); `calculate_gross_interest_for_term_deposit(td)` (`:39-58`); `calculate_net_interest_for_term_deposit(*, gross, costs, taxes)` (`:60-66`); `calculate_expected_maturity_value`; `calculate_days_until_maturity` (max-0 floor, `:79`); `derive_term_deposit_status` (date-only state machine); `build_term_deposit_projection` (orchestrator); aggregation helpers `calculate_total_term_deposit_value`, `calculate_total_net_term_deposit_interest`.

### Collaborators

`.money` (`ensure_same_currency`), `.errors`, stdlib `calendar` + `datetime`, `portfolio_outlook_domain` (`CurrencyCode`, `Money`, `TermDepositInput`, `TermDepositInterestType`, `TermDepositProjection`, `TermDepositStatus`, `TermDepositTerm`).

### Notable choices

- **Simple (non-compounding) interest** at `:51-57`: `principal × rate/100 × months/12`. No quantization — full Decimal precision flows into `Money`.
- Months converted via `Decimal(str(term_months(...)))` (`:50`) to keep exactness.
- Maturity-date EOM clamp: `day = min(start_date.day, calendar.monthrange(year, month)[1])` (`:35`) — a deposit started Jan 31 matures Feb 28/29.
- Cancellation short-circuits status to `CANCELLED` regardless of dates (`:108-110`).

```python
# term_deposits.py:39-58
def calculate_gross_interest_for_term_deposit(term_deposit: TermDepositInput) -> Money:
    if term_deposit.interest_type is TermDepositInterestType.FIXED_AMOUNT:
        if term_deposit.gross_interest_amount is None:
            raise InvalidAccountingInputError("gross_interest_amount is required for fixed_amount.")
        return term_deposit.gross_interest_amount

    if term_deposit.gross_interest_rate is None:
        raise InvalidAccountingInputError("gross_interest_rate is required for fixed_rate.")
    if term_deposit.gross_interest_rate.value < Decimal("0"):
        raise InvalidAccountingInputError("gross_interest_rate must be zero or positive.")

    months = Decimal(str(term_months(term_deposit.term)))
    gross_amount = (
        term_deposit.principal.amount
        * term_deposit.gross_interest_rate.value
        / Decimal("100")
        * months
        / Decimal("12")
    )
    return Money(amount=gross_amount, currency=term_deposit.principal.currency)
```

## `ledger_services.py` — ledger constructors + pair invariants

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/ledger_services.py`

### Public surface

- `create_deposit_cash_entry(...)` — requires positive amount; stores as positive.
- `create_withdrawal_cash_entry(...)` — accepts positive input, **stores negated** (`:80`).
- `build_paper_transaction(...)` — hard-wires `status=FILLED` and `mode=PAPER`; self-checks via `validate_transaction_amounts` (`:116-129`).
- `create_cash_entry_for_transaction(...)` — pairs a transaction with its ledger entry; defaults `reason_nl` and `occurred_at` to transaction values.
- `validate_cash_entry_sign(entry)` — canonical sign-convention enforcer (`:166-184`).
- `validate_transaction_cash_entry_pair(transaction, cash_entry)` — strongest cross-aggregate invariant (`:187-216`).
- Private `_require_non_empty_reason(reason_nl)` — used by every public constructor.

### Collaborators

`.accounting` (`calculate_cash_delta_for_transaction`, `calculate_gross_amount`, `calculate_net_transaction_amount`, `validate_transaction_amounts`), `.errors`, `portfolio_outlook_domain` (many — `CashLedgerEntry`, `LedgerEntryId`, `LedgerEntryType`, `PaperLiveMode`, `PaperTransaction`, `TransactionId`, etc.). No direct `money.py` import — routes through `accounting`.

### Notable choices

- **Sign convention is the persistent contract here.** DEPOSIT > 0, WITHDRAWAL/BUY/FEE/TAX_ESTIMATE < 0, SELL > 0. Enforced canonically by `validate_cash_entry_sign` (`:166-184`).
- `create_withdrawal_cash_entry` flips sign internally — callers pass magnitude, module owns sign.
- `build_paper_transaction` always sets `status=TransactionStatus.FILLED` and `mode=PaperLiveMode.PAPER` (`:116, :127`); no path for unfilled or live.
- After deriving values it invokes `validate_transaction_amounts(transaction)` (`:129`) — self-checks the values it just computed.

```python
# ledger_services.py:166-184
def validate_cash_entry_sign(entry: CashLedgerEntry) -> None:
    amount = entry.amount.amount
    entry_type = entry.entry_type

    if entry_type is LedgerEntryType.DEPOSIT and amount <= Decimal("0"):
        raise InvalidAccountingInputError("Deposit cash entry amount must be positive.")
    if entry_type is LedgerEntryType.WITHDRAWAL and amount >= Decimal("0"):
        raise InvalidAccountingInputError("Withdrawal cash entry amount must be negative.")
    if entry_type is LedgerEntryType.BUY and amount >= Decimal("0"):
        raise InvalidAccountingInputError("Buy cash entry amount must be negative.")
    if entry_type is LedgerEntryType.SELL and amount <= Decimal("0"):
        raise InvalidAccountingInputError("Sell cash entry amount must be positive.")
    if (entry_type in {LedgerEntryType.FEE, LedgerEntryType.TAX_ESTIMATE}
        and amount >= Decimal("0")):
        raise InvalidAccountingInputError(
            "Fee and tax_estimate cash entry amounts must be negative."
        )
```

## Cross-cutting observations

- **No `ROUND_HALF_EVEN` policy in this group.** `grep` across the package shows `ROUND_HALF_EVEN` is never imported anywhere in `portfolio_outlook_portfolio`; `quantize` is never called by modules 1–9 in this group. Banker's rounding is **not** the in-force policy here — raw `Decimal` arithmetic flows through. Other parts of the package use `ROUND_HALF_UP` (`belgian_tax.py:27`, `baseline_forecast.py:108`, `action_draft_safety.py:207-211`) or `ROUND_DOWN` (`kelly_sizing.py:48`, `action_draft_safety.py:203`).
- **Decimal-vs-float boundary is enforced at the domain layer** (`packages/domain/.../primitives.py:25-30, :42-45, :58-63`), not at the portfolio layer. `Money`, `Quantity`, `Percentage` reject float at construction.
- **Money-boundary check is centralised** in `money.ensure_same_currency`, reused by `accounting`, `performance`, `term_deposits`. Modules 6 and 7 deliberately bypass `Money` entirely (raw Decimal + string currencies + status-rich results).
- **FX-conversion lives in `valuation_conversion_totals.py`** — the only module combining values across currencies. It blocks/flags on missing/stale/invalid FX rather than raising. `valuation_cost_basis_pl.py` accepts already-converted values from the caller.
- **All target modules are stateless/pure-function.** Persistent state lives in the domain models they construct.
- **All non-trivial dataclasses are frozen** (`@dataclass(frozen=True)`); the only mutable struct is the private `_TotalsBucket` accumulator inside `snapshot.py:43-50`.

## Open questions / uncertainty

- `accounting.validate_transaction_amounts` uses `==` on `Money` (`accounting.py:64-77`). Whether this is rounding-sensitive in practice depends on what upstream callers feed in; without a rounding policy in the package, drift is theoretically possible. Out of scope for this Phase 1a doc; surfaces as a candidate gap.
- `lots.calculate_allocated_cost_basis` divides by `original_quantity` rather than `remaining_quantity`. Whether this matches the intent in `docs/intent/portfolio-valuation.md` §1 ("Lot granularity is the floor; aggregation is reporting") is not assessed here.
- `performance.calculate_cash_flow_summary` `abs()`-normalises withdrawals (`performance.py:69`) but the storage convention (per `ledger_services.validate_cash_entry_sign`) stores withdrawals negative. The double convention works only if consumers of `cash_entries` are aware of both signs; whether all callers are aware is out of scope here.
- `valuation_conversion_totals.py` and `valuation_cost_basis_pl.py` deliberately bypass `Money`. Whether this is by design (boundary modules return Decimal + status codes for UI rendering) or candidate for unification will be assessed by Phase 1b architecture review.
