"""Pure-Python action-draft sizing, Orderimpact and dry-run safety checks.

V1 scope (locked):

* stocks/ETFs only, whole shares only
* ``LMT`` order type only
* ``DAY`` tif only
* ``BUY`` or ``SELL`` action side only
* Markets: NYSE, Nasdaq, Euronext Brussels/Amsterdam/Paris, Xetra

The module is stdlib only. The orchestrator that calls it is responsible
for sourcing the inputs (Decision Package, position, cash, market and FX
snapshots, account-mode settings) and for persisting the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Final

from .belgian_tax import TobSecurityClass, compute_tob

# Locked sizing constants ---------------------------------------------------

DEFAULT_BUY_VALUE_EUR: Final[Decimal] = Decimal("1000")
DEFAULT_TOP_UP_PCT: Final[Decimal] = Decimal("0.25")
DEFAULT_REDUCE_PCT: Final[Decimal] = Decimal("0.25")

LOCKED_ALLOWED_EXCHANGES: Final[frozenset[str]] = frozenset(
    {
        "NYSE",
        "NASDAQ",
        "NMS",
        "ARCA",
        "AMEX",
        "BATS",
        "AEB",
        "EBR",
        "BRU",
        "SBF",
        "EPA",
        "ENEXT.BE",
        "ENEXT.LIS",
        "IBIS",
        "IBIS2",
        "XETR",
    }
)

LOCKED_ORDER_TYPE: Final = "LMT"
LOCKED_TIF: Final = "DAY"
LOCKED_ACTION_SIDES: Final[frozenset[str]] = frozenset({"BUY", "SELL"})


# Action labels that produce actionable drafts. ``Houden``, ``Bekijken``,
# ``Geen actie``, ``Vermijden``, ``Cash houden`` and ``Geblokkeerd`` do NOT
# produce drafts.
ACTIONABLE_LABELS_BUY: Final[frozenset[str]] = frozenset(
    {"Kopen", "Langzaam bijkopen"}
)
ACTIONABLE_LABELS_SELL: Final[frozenset[str]] = frozenset({"Verminderen", "Verkopen"})
ACTIONABLE_LABELS: Final[frozenset[str]] = ACTIONABLE_LABELS_BUY | ACTIONABLE_LABELS_SELL


# Inputs / outputs -----------------------------------------------------------


@dataclass(frozen=True)
class DraftSourceContext:
    """All evidence the orchestrator hands to the sizing+dry-run engine.

    Decimals are exact. Optional fields are explicitly ``None`` when the
    upstream evidence is missing — the dry-run will report the corresponding
    failure rather than silently substituting a value.
    """

    decision_package_id: str
    decision_package_content_hash: str
    ibkr_conid: str
    symbol: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    account_mode: str
    expected_account_mode: str
    action_label: str
    action_label_nl: str
    rationale_nl: str
    current_position_quantity: Decimal
    current_position_average_cost: Decimal | None
    current_market_last_price: Decimal | None
    current_market_freshness_status: str | None
    cash_amount: Decimal | None
    cash_currency: str | None
    fx_required: bool
    fx_freshness_status: str | None
    total_portfolio_value: Decimal | None
    base_currency: str | None


@dataclass(frozen=True)
class DraftSizing:
    """Outcome of sizing logic. ``status`` is ``ready`` only when the math
    produced a positive whole-share quantity at a positive limit price."""

    action_side: str
    quantity: Decimal
    limit_price: Decimal
    status: str  # "ready" | "blocked"
    blocking_reason: str | None


@dataclass(frozen=True)
class Orderimpact:
    """Result of the Orderimpact math (cash and position before/after)."""

    estimated_order_value: Decimal
    estimated_cash_before: Decimal | None
    estimated_cash_after: Decimal | None
    estimated_position_quantity_before: Decimal
    estimated_position_quantity_after: Decimal
    estimated_position_value_after: Decimal
    estimated_portfolio_weight_after_pct: Decimal | None
    estimated_concentration_impact_pct: Decimal | None
    base_currency: str | None
    estimated_belgian_tob: Decimal
    belgian_tob_security_class: str


@dataclass(frozen=True)
class DryRunResult:
    """Pass/fail outcome of the deterministic safety check pass."""

    status: str  # "passed" | "failed"
    failures: tuple[str, ...]


# Sizing ---------------------------------------------------------------------


def _whole_shares(value: Decimal) -> Decimal:
    """Floor to a whole-share quantity. Negative inputs return 0."""

    if value <= 0:
        return Decimal("0")
    return value.to_integral_value(rounding=ROUND_DOWN)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _percentage(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def derive_action_draft_sizing(
    context: DraftSourceContext,
    *,
    default_buy_value_in_quote_currency: Decimal = DEFAULT_BUY_VALUE_EUR,
    top_up_pct: Decimal = DEFAULT_TOP_UP_PCT,
    reduce_pct: Decimal = DEFAULT_REDUCE_PCT,
) -> DraftSizing:
    """Derive the locked-scope (LMT/DAY/whole-share) sizing from the
    suggestion label + the held position.

    BUY paths (``Kopen``, ``Langzaam bijkopen``) require a positive market
    price to convert capital to shares; without it the sizing is blocked
    rather than guessed.

    SELL paths (``Verminderen``, ``Verkopen``) require the asset to be held.
    """

    label = context.action_label
    if label not in ACTIONABLE_LABELS:
        return DraftSizing(
            action_side="BUY",
            quantity=Decimal("0"),
            limit_price=Decimal("0"),
            status="blocked",
            blocking_reason="not_actionable_label",
        )

    market_price = context.current_market_last_price
    if market_price is None or market_price <= 0:
        return DraftSizing(
            action_side="BUY" if label in ACTIONABLE_LABELS_BUY else "SELL",
            quantity=Decimal("0"),
            limit_price=Decimal("0"),
            status="blocked",
            blocking_reason="missing_market_price",
        )

    limit_price = _money(market_price)

    if label == "Kopen":
        capital = default_buy_value_in_quote_currency
        quantity = _whole_shares(capital / limit_price)
        if quantity <= 0:
            return DraftSizing(
                action_side="BUY",
                quantity=Decimal("0"),
                limit_price=limit_price,
                status="blocked",
                blocking_reason="buy_value_too_small_for_one_share",
            )
        return DraftSizing("BUY", quantity, limit_price, "ready", None)

    if label == "Langzaam bijkopen":
        held = context.current_position_quantity
        if held <= 0:
            # No held shares to top up; fall back to a default-sized buy.
            capital = default_buy_value_in_quote_currency
            quantity = _whole_shares(capital / limit_price)
        else:
            quantity = _whole_shares(held * top_up_pct)
            if quantity <= 0:
                quantity = Decimal("1")  # tiny held position -> 1 share top-up
        return DraftSizing("BUY", quantity, limit_price, "ready", None)

    # SELL branch (``Verminderen`` / ``Verkopen``)
    held = context.current_position_quantity
    if held <= 0:
        return DraftSizing(
            action_side="SELL",
            quantity=Decimal("0"),
            limit_price=limit_price,
            status="blocked",
            blocking_reason="no_held_position_to_sell",
        )
    if label == "Verkopen":
        return DraftSizing("SELL", _whole_shares(held), limit_price, "ready", None)
    # ``Verminderen``
    quantity = _whole_shares(held * reduce_pct)
    if quantity <= 0:
        quantity = Decimal("1")
    return DraftSizing("SELL", quantity, limit_price, "ready", None)


# Orderimpact ---------------------------------------------------------------


def compute_orderimpact(
    context: DraftSourceContext,
    sizing: DraftSizing,
    *,
    belgian_tob_security_class: TobSecurityClass = TobSecurityClass.STANDARD_STOCK,
) -> Orderimpact:
    """Compute the deterministic Orderimpact preview from the sizing.

    ``belgian_tob_security_class`` controls which TOB rate is applied
    to the estimated_belgian_tob field. V1 default is
    ``STANDARD_STOCK`` (0.35%) because the action-draft scope is
    locked to listed shares.
    """

    quantity = sizing.quantity
    limit_price = sizing.limit_price
    order_value = _money(quantity * limit_price)

    pos_before = context.current_position_quantity
    if sizing.action_side == "BUY":
        pos_after = pos_before + quantity
        cash_delta = -order_value
    else:
        pos_after = pos_before - quantity
        cash_delta = order_value

    if context.cash_amount is not None and context.cash_currency == context.currency:
        cash_before: Decimal | None = _money(context.cash_amount)
        cash_after: Decimal | None = _money(context.cash_amount + cash_delta)
    elif context.cash_amount is not None and not context.fx_required:
        cash_before = _money(context.cash_amount)
        cash_after = _money(context.cash_amount + cash_delta)
    else:
        # When the order currency differs from the cash currency we don't
        # apply an FX rate here; the orchestrator surfaces the FX gate
        # outcome in the dry-run summary instead.
        cash_before = None
        cash_after = None

    pos_value_after = _money(pos_after * limit_price)
    weight_after = None
    concentration = None
    if context.total_portfolio_value is not None and context.total_portfolio_value > 0:
        weight_after = _percentage(
            (pos_value_after / context.total_portfolio_value) * Decimal("100")
        )
        before_value = _money(pos_before * limit_price)
        before_weight = (before_value / context.total_portfolio_value) * Decimal("100")
        concentration = _percentage(weight_after - before_weight)

    belgian_tob = compute_tob(
        transaction_value=order_value,
        security_class=belgian_tob_security_class,
    )

    return Orderimpact(
        estimated_order_value=order_value,
        estimated_cash_before=cash_before,
        estimated_cash_after=cash_after,
        estimated_position_quantity_before=pos_before,
        estimated_position_quantity_after=pos_after,
        estimated_position_value_after=pos_value_after,
        estimated_portfolio_weight_after_pct=weight_after,
        estimated_concentration_impact_pct=concentration,
        base_currency=context.base_currency,
        estimated_belgian_tob=belgian_tob,
        belgian_tob_security_class=belgian_tob_security_class.value,
    )


# Dry-run --------------------------------------------------------------------


def run_dry_run_safety_checks(
    context: DraftSourceContext,
    sizing: DraftSizing,
    orderimpact: Orderimpact,
) -> DryRunResult:
    """Run the deterministic safety checks documented in the doctrine.

    Failures are returned as stable string codes; the orchestrator can map
    them to a Dutch UI string. A dry-run with any failure means the draft
    is **not** safe to submit. The persisted record additionally keeps
    ``safe_for_*=False`` so this slice can never feed a broker submission
    even if the dry-run passes — submission lives in a later slice.
    """

    failures: list[str] = []

    if sizing.status != "ready":
        return DryRunResult(
            status="failed",
            failures=(sizing.blocking_reason or "sizing_blocked",),
        )

    if not context.ibkr_conid.strip():
        failures.append("missing_ibkr_conid")

    # Account-mode gate: paper-only safety net for V1; the locked product
    # rule allows visible paper/real-money context, but mismatch always
    # fails dry-run.
    expected = (context.expected_account_mode or "").strip().lower()
    actual = (context.account_mode or "").strip().lower()
    if not expected or not actual:
        failures.append("missing_account_mode")
    elif expected != actual:
        failures.append("account_mode_mismatch")

    # Exchange whitelist gate
    primary = (context.primary_exchange or context.exchange or "").strip().upper()
    if not primary:
        failures.append("missing_exchange")
    elif primary not in LOCKED_ALLOWED_EXCHANGES:
        failures.append("unsupported_exchange")

    # Market-data freshness gate
    market_freshness = (context.current_market_freshness_status or "").strip().lower()
    if market_freshness != "fresh":
        failures.append("market_data_not_fresh")

    # FX freshness gate (only when FX is actually required)
    if context.fx_required:
        fx_freshness = (context.fx_freshness_status or "").strip().lower()
        if fx_freshness != "fresh":
            failures.append("fx_not_fresh")

    # Cash gate for BUY: order value must not exceed available cash when we
    # can actually compare them (same currency / no FX needed).
    if sizing.action_side == "BUY":
        if orderimpact.estimated_cash_before is None:
            # Missing cash comparison is itself a failure on a BUY draft.
            failures.append("cash_comparison_unavailable")
        else:
            if orderimpact.estimated_cash_before < orderimpact.estimated_order_value:
                failures.append("buy_value_exceeds_usable_cash")

    # Sell-quantity gate
    if sizing.action_side == "SELL":
        if sizing.quantity > context.current_position_quantity:
            failures.append("sell_quantity_exceeds_held")

    # Quantity / price sanity (redundant with __post_init__ on the record,
    # but the dry-run reports it explicitly so the user knows).
    if sizing.quantity <= 0:
        failures.append("invalid_quantity")
    if sizing.limit_price <= 0:
        failures.append("invalid_limit_price")

    return DryRunResult(
        status="passed" if not failures else "failed",
        failures=tuple(failures),
    )
