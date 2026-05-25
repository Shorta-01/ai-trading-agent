"""Pure-Python action-draft sizing, Orderimpact and dry-run safety checks.

V1 scope (locked):

* stocks/ETFs only, whole shares only
* order types: ``LMT``, ``MKT``, ``STP``, ``STP_LMT``, ``TRAIL``,
  ``TRAIL_LMT``, ``BRACKET`` (per §21.3)
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
LOCKED_ORDER_TYPES: Final[frozenset[str]] = frozenset(
    {"LMT", "MKT", "STP", "STP_LMT", "TRAIL", "TRAIL_LMT", "BRACKET"}
)
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
    # Kelly-sizing context (Slice 19). Optional — when any of these is
    # ``None`` the BUY path falls back to the legacy
    # default-buy-value sizing rather than guessing.
    ensemble_prob_gain: Decimal | None = None
    ensemble_expected_return_pct: Decimal | None = None
    ensemble_downside_loss_pct: Decimal | None = None
    current_sector_exposure_pct: Decimal | None = None
    current_portfolio_position_count: int | None = None


@dataclass(frozen=True)
class DraftConditionCheck:
    """One activation-condition check for a CONDITIONAL action draft.

    Mirrors the shape of ``ActionDraftOrderConditionRecord`` but stays
    pure-Python so the dry-run can operate without a storage round-
    trip. ``condition_kind`` is one of
    ``{"price", "time", "margin", "volume", "execution"}``.
    """

    condition_kind: str
    comparator: str
    trigger_price: Decimal | None = None
    trigger_at_utc: object | None = None  # datetime | None at use site
    margin_percent: Decimal | None = None
    trigger_volume: int | None = None


@dataclass(frozen=True)
class DraftSizing:
    """Outcome of sizing logic. ``status`` is ``ready`` only when the math
    produced a positive whole-share quantity (and the price fields the
    chosen order type requires are all positive).

    ``order_type`` defaults to ``LMT`` to keep callers that only handle
    plain limit orders unchanged. The extra price fields are only set
    when the orchestrator emits a non-LMT order (§21.3 vocabulary).
    """

    action_side: str
    quantity: Decimal
    limit_price: Decimal
    status: str  # "ready" | "blocked"
    blocking_reason: str | None
    order_type: str = "LMT"
    stop_price: Decimal | None = None
    trail_amount: Decimal | None = None
    trail_percent: Decimal | None = None
    bracket_take_profit_limit_price: Decimal | None = None
    bracket_stop_loss_price: Decimal | None = None
    # V1.1 §22.3 CONDITIONAL parent base type. Required when
    # ``order_type == "CONDITIONAL"``.
    conditional_parent_order_type: str | None = None
    # V1.1 §22.3 conditions list — the dry-run iterates this and emits
    # stable per-kind failure codes. Default empty so non-conditional
    # callers stay unchanged.
    conditions: tuple[DraftConditionCheck, ...] = ()
    # V1.1 §22.3 time-in-force. Default DAY keeps V1 behaviour.
    tif: str = "DAY"
    # V1.1 §22.3 — whether the IBKR account is paper (so GTC may have
    # different fill semantics than a live account). The dry-run uses
    # this to surface a `tif_gtc_requires_real_account` warning when
    # the operator wants GTC on a paper account.
    paper_mode: bool = True


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


def _resolve_kopen_capital(
    context: DraftSourceContext,
    *,
    default_buy_value: Decimal,
) -> Decimal:
    """Decide how much capital to spend on a ``Kopen`` draft.

    Fractional Kelly + risk-parity caps (§21.5) when the ensemble's
    `prob_gain` / `expected_return` / `downside_loss` are available
    *and* the operator has both usable cash and a known portfolio
    value. Falls back to the legacy default-buy-value when the
    ensemble inputs are missing.
    """

    prob_gain = context.ensemble_prob_gain
    expected_return = context.ensemble_expected_return_pct
    downside_loss = context.ensemble_downside_loss_pct
    portfolio_value = context.total_portfolio_value
    cash_amount = context.cash_amount
    if (
        prob_gain is None
        or expected_return is None
        or downside_loss is None
        or portfolio_value is None
        or portfolio_value <= 0
        or cash_amount is None
        or cash_amount <= 0
    ):
        return default_buy_value

    raw_fraction = _kelly_fraction(
        prob_gain=prob_gain,
        expected_return_pct=expected_return,
        downside_loss_pct=downside_loss,
    )
    capped = _kelly_apply_caps(
        fraction=raw_fraction,
        sector_exposure_pct=context.current_sector_exposure_pct,
    )
    if capped <= 0:
        return Decimal("0")
    # Per-asset position size is a fraction of portfolio value, but the
    # cash needed to BUY is capped by available cash to avoid taking
    # the position negative on the cash side.
    target_capital = (capped * portfolio_value)
    return min(target_capital, cash_amount)


def _kelly_fraction(
    *,
    prob_gain: Decimal,
    expected_return_pct: Decimal,
    downside_loss_pct: Decimal,
) -> Decimal:
    """Local shim around `kelly_sizing.compute_fractional_kelly_fraction`
    that defaults to half-Kelly (the V1 §21.5 lock)."""

    from .kelly_sizing import compute_fractional_kelly_fraction

    return compute_fractional_kelly_fraction(
        prob_gain=prob_gain,
        expected_return_pct=expected_return_pct,
        downside_loss_pct=downside_loss_pct,
    )


def _kelly_apply_caps(
    *,
    fraction: Decimal,
    sector_exposure_pct: Decimal | None,
) -> Decimal:
    """Local shim that returns only the final (capped) fraction."""

    from .kelly_sizing import apply_risk_parity_caps

    return apply_risk_parity_caps(
        fraction=fraction,
        current_sector_exposure_pct=sector_exposure_pct,
    ).fraction


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
        # §21.5 fractional Kelly + risk-parity caps replace the
        # fixed-buy-value sizing **when the ensemble distribution is
        # available**. Without an ensemble we keep the legacy
        # default-buy-value behaviour rather than guess.
        capital = _resolve_kopen_capital(
            context,
            default_buy_value=default_buy_value_in_quote_currency,
        )
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

    # Account-mode is informational only since the V1 §21 relock — the
    # connected IBKR account decides paper vs. live, not an app-side
    # gate. We still record both values on the draft for audit, but a
    # missing or differing mode no longer blocks dry-run. The remaining
    # safety surface is per-draft manual approval + the broker's own
    # account selection.
    actual = (context.account_mode or "").strip().lower()
    if not actual:
        failures.append("missing_account_mode")

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
    # ``limit_price`` is only required for order types that carry one
    # (everything except MKT, STP and TRAIL). Plain TRAIL has only an
    # offset; STP only has a stop price. MKT has neither.
    if sizing.order_type in {"LMT", "STP_LMT", "TRAIL_LMT", "BRACKET"}:
        if sizing.limit_price <= 0:
            failures.append("invalid_limit_price")

    # Per-order-type extras (§21.3 vocabulary).
    _append_per_order_type_failures(sizing, failures)

    # V1.1 §22.3 TIF + conditional extras.
    _append_v1_1_tif_and_conditional_failures(sizing, failures)

    return DryRunResult(
        status="passed" if not failures else "failed",
        failures=tuple(failures),
    )


_LOCKED_TIF_SET: frozenset[str] = frozenset({"DAY", "GTC", "OPG", "IOC"})
_LOCKED_CONDITIONAL_PARENT_TYPES: frozenset[str] = frozenset(
    {"LMT", "MKT", "STP", "STP_LMT"}
)
_LOCKED_CONDITION_KINDS: frozenset[str] = frozenset(
    {"price", "time", "margin", "volume", "execution"}
)


def _append_v1_1_tif_and_conditional_failures(
    sizing: DraftSizing,
    failures: list[str],
) -> None:
    """V1.1 §22.3 — extra dry-run gates for the new TIF set and
    CONDITIONAL order type.

    Stable failure codes:

    * ``tif_unsupported`` — sizing.tif outside the §22.3 lock
    * ``tif_gtc_requires_real_account`` — GTC chosen on paper mode
    * ``conditional_missing_parent_order_type``
    * ``conditional_unknown_parent_order_type``
    * ``conditional_no_conditions_listed``
    * ``conditional_unknown_condition_kind``
    * ``conditional_price_missing_trigger``
    * ``conditional_time_missing_trigger``
    * ``conditional_margin_invalid_percent``
    """

    if sizing.tif not in _LOCKED_TIF_SET:
        failures.append("tif_unsupported")
    elif sizing.tif == "GTC" and sizing.paper_mode:
        failures.append("tif_gtc_requires_real_account")

    if sizing.order_type != "CONDITIONAL":
        return
    parent = sizing.conditional_parent_order_type
    if not parent:
        failures.append("conditional_missing_parent_order_type")
    elif parent not in _LOCKED_CONDITIONAL_PARENT_TYPES:
        failures.append("conditional_unknown_parent_order_type")
    if not sizing.conditions:
        failures.append("conditional_no_conditions_listed")
        return
    for cond in sizing.conditions:
        if cond.condition_kind not in _LOCKED_CONDITION_KINDS:
            failures.append("conditional_unknown_condition_kind")
            continue
        if cond.condition_kind == "price":
            if cond.trigger_price is None or cond.trigger_price <= 0:
                failures.append("conditional_price_missing_trigger")
        elif cond.condition_kind == "time":
            if cond.trigger_at_utc is None:
                failures.append("conditional_time_missing_trigger")
        elif cond.condition_kind == "margin":
            pct = cond.margin_percent
            if pct is None or pct < 0 or pct > Decimal("100"):
                failures.append("conditional_margin_invalid_percent")


def _append_per_order_type_failures(
    sizing: DraftSizing,
    failures: list[str],
) -> None:
    """Validate the order-type-specific extras on a ``DraftSizing``.

    Stable failure codes (mapped to Dutch UI strings by the orchestrator):

    * ``unsupported_order_type`` — order_type outside the §21.3 lock
    * ``stp_missing_stop_price``, ``stp_lmt_missing_stop_or_limit``
    * ``trail_missing_trail_value``, ``trail_amount_and_percent_set``
    * ``trail_lmt_missing_limit_price``
    * ``bracket_missing_take_profit``, ``bracket_missing_stop_loss``
    * ``bracket_take_profit_below_limit``, ``bracket_stop_loss_above_limit``
    * ``bracket_inverted_for_sell``
    """

    order_type = sizing.order_type
    if order_type not in LOCKED_ORDER_TYPES:
        failures.append("unsupported_order_type")
        return

    if order_type == "STP":
        if sizing.stop_price is None or sizing.stop_price <= 0:
            failures.append("stp_missing_stop_price")
        return

    if order_type == "STP_LMT":
        stop_ok = sizing.stop_price is not None and sizing.stop_price > 0
        limit_ok = sizing.limit_price > 0
        if not stop_ok or not limit_ok:
            failures.append("stp_lmt_missing_stop_or_limit")
        return

    if order_type in {"TRAIL", "TRAIL_LMT"}:
        has_amount = sizing.trail_amount is not None and sizing.trail_amount > 0
        has_percent = sizing.trail_percent is not None and sizing.trail_percent > 0
        if not has_amount and not has_percent:
            failures.append("trail_missing_trail_value")
        elif has_amount and has_percent:
            failures.append("trail_amount_and_percent_set")
        if order_type == "TRAIL_LMT" and sizing.limit_price <= 0:
            failures.append("trail_lmt_missing_limit_price")
        return

    if order_type == "BRACKET":
        tp = sizing.bracket_take_profit_limit_price
        sl = sizing.bracket_stop_loss_price
        if tp is None or tp <= 0:
            failures.append("bracket_missing_take_profit")
        if sl is None or sl <= 0:
            failures.append("bracket_missing_stop_loss")
        if (
            tp is not None
            and sl is not None
            and tp > 0
            and sl > 0
            and sizing.limit_price > 0
        ):
            if sizing.action_side == "BUY":
                if tp <= sizing.limit_price:
                    failures.append("bracket_take_profit_below_limit")
                if sl >= sizing.limit_price:
                    failures.append("bracket_stop_loss_above_limit")
            else:  # SELL
                if tp >= sizing.limit_price or sl <= sizing.limit_price:
                    failures.append("bracket_inverted_for_sell")
