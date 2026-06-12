"""Bridge from profit-harvest take-profit pairs to the IBKR submission
client (V1.2 §U).

The profit-harvest orchestrator (V1.2 §M) produces a
:class:`TakeProfitOrderPair` — entry LMT + take-profit LMT, no
stop-loss. This adapter converts that pair into the
:class:`OrderSubmissionInputs` shape the IBKR submission client
expects, using ``order_type='BRACKET'`` with the locked doctrine
signal ``bracket_stop_loss_price=None`` so the submission client
builds a 2-leg bracket instead of 3.

Why a separate module? The submission client lives in the API; the
take-profit pair lives in the portfolio package. Keeping the
adapter at the API boundary preserves the leaf-pure status of the
portfolio package — no API types leak down, no broker types leak
up.

Pure Python: no I/O, no datetime, no IBKR types — just dataclass
re-shaping plus per-field validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from portfolio_outlook_portfolio import TakeProfitOrderPair

from portfolio_outlook_api.ibkr_ibapi_order_submission_client import (
    OrderSubmissionInputs,
)

# Locked V1 contract defaults — the submission client requires these
# fields and they're always the same for the profit-harvest doctrine
# (US stock, USD, STK security type). Callers can override per-pair
# when needed (e.g. EUR-quoted European venues).
DEFAULT_PRIMARY_EXCHANGE: Final[str] = "NASDAQ"
DEFAULT_CURRENCY: Final[str] = "USD"
DEFAULT_SECURITY_TYPE: Final[str] = "STK"
DEFAULT_BUY_ACTION_SIDE: Final[str] = "BUY"


@dataclass(frozen=True)
class ConvertedTakeProfitSubmission:
    """The result of converting one pair.

    ``inputs`` carries everything the submission client needs to
    place a 2-leg bracket (parent LMT entry + take-profit LMT exit,
    no stop-loss). The dataclass is frozen so the conversion result
    can't be mutated between adapter and submission layer.
    """

    inputs: OrderSubmissionInputs


def pair_to_submission_inputs(
    pair: TakeProfitOrderPair,
    *,
    primary_exchange: str = DEFAULT_PRIMARY_EXCHANGE,
    currency: str = DEFAULT_CURRENCY,
    security_type: str = DEFAULT_SECURITY_TYPE,
) -> ConvertedTakeProfitSubmission:
    """Convert a profit-harvest pair into submission inputs.

    Produces a single ``OrderSubmissionInputs`` with
    ``order_type='BRACKET'`` and ``bracket_stop_loss_price=None``.
    The submission client's BRACKET branch detects the missing
    stop-loss and emits a 2-leg bracket (parent + take-profit)
    instead of the 3-leg one.

    Args:
        pair: The take-profit pair produced by the orchestrator's
            :func:`build_take_profit_pair`.
        primary_exchange: IBKR exchange routing code. Defaults to
            ``"NASDAQ"`` because the V1 universe is US large-caps.
        currency: Contract currency. Defaults to ``"USD"``.
        security_type: IBKR security type. Defaults to ``"STK"``;
            the submission client rejects anything else in V1.

    Returns:
        :class:`ConvertedTakeProfitSubmission` ready to feed the
        submission client.

    Raises:
        ValueError: if ``pair.qty`` is not a positive integer, or
            either price is non-positive. The orchestrator's pair
            builder enforces these invariants but we re-check at the
            boundary to prevent integration bugs from reaching IBKR.
    """

    if pair.qty <= 0 or not isinstance(pair.qty, int):
        raise ValueError("pair.qty must be a positive int")
    if pair.entry_lmt_price <= 0:
        raise ValueError("pair.entry_lmt_price must be > 0")
    if pair.take_profit_sell_price <= 0:
        raise ValueError("pair.take_profit_sell_price must be > 0")
    if pair.take_profit_sell_price <= pair.entry_lmt_price:
        raise ValueError(
            "pair.take_profit_sell_price must be > entry_lmt_price"
        )
    if not primary_exchange.strip():
        raise ValueError("primary_exchange must be non-empty")
    if not currency.strip():
        raise ValueError("currency must be non-empty")
    if not security_type.strip():
        raise ValueError("security_type must be non-empty")

    return ConvertedTakeProfitSubmission(
        inputs=OrderSubmissionInputs(
            symbol=pair.ticker,
            primary_exchange=primary_exchange,
            currency=currency,
            security_type=security_type,
            action_side=DEFAULT_BUY_ACTION_SIDE,
            quantity=Decimal(pair.qty),
            limit_price=pair.entry_lmt_price,
            order_type="BRACKET",
            bracket_take_profit_limit_price=pair.take_profit_sell_price,
            # Locked doctrine signal: no stop-loss. The submission
            # client's BRACKET branch detects this and emits the
            # 2-leg bracket.
            bracket_stop_loss_price=None,
        ),
    )


__all__ = [
    "DEFAULT_BUY_ACTION_SIDE",
    "DEFAULT_CURRENCY",
    "DEFAULT_PRIMARY_EXCHANGE",
    "DEFAULT_SECURITY_TYPE",
    "ConvertedTakeProfitSubmission",
    "pair_to_submission_inputs",
]
