"""Task 134: pure-function order builder.

The only place in the codebase where Decimal crosses to float. The
Action Draft + the tick-size record (fetched per submission per
Task 134 product lock §5) come in; an ``ib_insync.Contract`` + an
``ib_insync.Order`` go out, with the limit price quantized to the
contract's tick size and the side / order_type / time_in_force
copied verbatim from the draft.

``ib_insync`` is imported lazily inside ``build_ib_order`` so the
module stays importable in test paths that don't have ``ib_insync``
installed (the gate + Decimal-boundary tests in 134a). The lazy
import also keeps the api package from accidentally pulling ib_insync
through the worker dep chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from ai_trading_agent_storage import ActionDraftEntry


@dataclass(frozen=True)
class TickSize:
    """Contract tick-size descriptor, fetched per submission.

    For ASML on Euronext the tick size is ``Decimal("0.005")``.
    Equity tick sizes are typically simple powers of ten plus halves;
    the exotic dynamic-tick contracts (US options below $3, etc.) are
    out of scope for V1 because Task 134 only ships LMT for stocks +
    ETFs.
    """

    tick_size_local: Decimal
    min_lot_size: Decimal = Decimal("1")


class LimitPriceNotOnTickSizeError(ValueError):
    """Raised when the draft's limit price cannot be aligned to tick size.

    Task 134 lock §3 makes ``tick_size_invalid`` a blocking reason —
    this exception is the storage-layer event the safety_recheck path
    converts into that block. ``build_ib_order`` raises before
    touching ``ib_insync`` so the audit row records the failure
    cleanly without a network call.
    """


def round_to_tick_size(
    *, price_local: Decimal, tick: TickSize
) -> Decimal:
    """Quantize ``price_local`` to the nearest tick using banker's rounding.

    Banker's rounding (``ROUND_HALF_EVEN``) avoids the systematic bias
    of always-round-up; the spread between adjacent ticks is at most
    half a tick, which is within IBKR's accept window for LMT orders.
    """

    if tick.tick_size_local <= 0:
        raise LimitPriceNotOnTickSizeError(
            f"tick_size_local must be positive, got {tick.tick_size_local}"
        )
    ratio = (price_local / tick.tick_size_local).quantize(
        Decimal("1"), rounding=ROUND_HALF_EVEN
    )
    return (ratio * tick.tick_size_local).quantize(
        tick.tick_size_local
    )


def build_ib_order(
    *,
    draft: ActionDraftEntry,
    tick: TickSize,
    conid: int | None = None,
) -> tuple[Any, Any]:
    """Build ``(Contract, Order)`` for ``ib_insync.IB.placeOrder()``.

    The returned objects are ``ib_insync.Contract`` and
    ``ib_insync.Order`` — typed as ``Any`` because we lazy-import the
    library so the module loads in test paths without ``ib_insync``
    installed. Production callers get the real classes; tests can
    inject fakes via the alternative builder factories.

    The Decimal → float boundary lives in this function and nowhere
    else. After this call returns, the rest of the system still
    receives Decimal-typed values from the audit/lifecycle layer; the
    floats are owned by IB Insync only.
    """

    if draft.quantity <= 0:
        raise ValueError("draft.quantity must be positive")
    if draft.limit_price_local <= 0:
        raise ValueError("draft.limit_price_local must be positive")
    if draft.order_type != "LMT":
        raise ValueError(
            f"order_type {draft.order_type!r}; Task 134 only supports LMT"
        )
    if draft.time_in_force != "DAY":
        raise ValueError(
            f"time_in_force {draft.time_in_force!r}; Task 134 only supports DAY"
        )
    if draft.side not in {"BUY", "SELL"}:
        raise ValueError(f"side {draft.side!r} not in {{BUY, SELL}}")

    rounded_limit = round_to_tick_size(
        price_local=draft.limit_price_local, tick=tick
    )
    # If rounding shifted the price by more than one tick, the original
    # price was off-grid by definition — fail loudly so the audit
    # path records ``tick_size_invalid`` and the user can re-approve.
    drift = abs(rounded_limit - draft.limit_price_local)
    if drift > tick.tick_size_local:
        raise LimitPriceNotOnTickSizeError(
            f"limit_price_local {draft.limit_price_local} cannot be "
            f"aligned to tick_size {tick.tick_size_local} without "
            f"drifting more than one tick (drift={drift})."
        )

    from ib_insync import Contract, Order

    contract = Contract(
        secType="STK",
        symbol=draft.symbol,
        exchange=draft.exchange,
        currency=draft.currency_local,
    )
    if conid is not None:
        contract.conId = conid

    # The Decimal → float boundary. Past this point, the IB Insync
    # objects own the numeric values; nothing else in the system
    # touches these floats.
    order = Order(
        action=draft.side,
        totalQuantity=float(draft.quantity),
        orderType="LMT",
        lmtPrice=float(rounded_limit),
        tif="DAY",
        outsideRth=False,
    )
    return contract, order
