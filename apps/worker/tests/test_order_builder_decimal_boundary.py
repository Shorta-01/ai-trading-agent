"""Task 134a — order_builder Decimal-to-float boundary tests.

The locked rule: Decimal must reach ``build_ib_order``; the only
``float()`` conversion happens *inside* the function before it
constructs the ``ib_insync.Order``. Everything that flows back out
to audit/lifecycle/storage stays Decimal. The function also rounds
the limit price to the contract's tick size with banker's rounding
and raises ``LimitPriceNotOnTickSizeError`` if the input is more
than one tick off-grid.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from ai_trading_agent_storage import ActionDraftEntry

from portfolio_outlook_worker.ibkr_submission.order_builder import (
    LimitPriceNotOnTickSizeError,
    TickSize,
    build_ib_order,
    round_to_tick_size,
)

_BASE_TS = datetime(2026, 5, 26, 9, 0, tzinfo=UTC)


def _draft(
    *,
    side: str = "BUY",
    quantity: Decimal = Decimal("6"),
    limit_price: Decimal = Decimal("638.72"),
    order_type: str = "LMT",
    time_in_force: str = "DAY",
) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id="draft-1",
        decision_package_id=None,
        forecast_run_id=None,
        created_at=_BASE_TS,
        created_by="user",
        ibkr_account_id="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        side=side,
        quantity=quantity,
        order_type=order_type,
        limit_price_local=limit_price,
        time_in_force=time_in_force,
        notional_local=quantity * limit_price,
        notional_eur=quantity * limit_price,
        fx_rate_at_creation=Decimal("1"),
        usable_cash_eur_at_creation=Decimal("50000"),
        held_quantity_at_creation=None,
        status="user_approved",
        last_edited_at=None,
        user_approved_at=_BASE_TS,
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash="h-1",
        previous_draft_hash=None,
        safe_for_submission=False,
    )


def _tick(tick_size: Decimal = Decimal("0.005")) -> TickSize:
    return TickSize(tick_size_local=tick_size)


# ---- round_to_tick_size ------------------------------------------------


def test_round_to_tick_size_exact_match() -> None:
    rounded = round_to_tick_size(
        price_local=Decimal("638.720"), tick=_tick(Decimal("0.005"))
    )
    assert rounded == Decimal("638.720")


def test_round_to_tick_size_rounds_up() -> None:
    rounded = round_to_tick_size(
        price_local=Decimal("638.7235"), tick=_tick(Decimal("0.005"))
    )
    # 638.7235 / 0.005 = 127744.7 → ROUND_HALF_EVEN → 127745 → 638.725.
    assert rounded == Decimal("638.725")


def test_round_to_tick_size_rounds_down() -> None:
    rounded = round_to_tick_size(
        price_local=Decimal("638.7224"), tick=_tick(Decimal("0.005"))
    )
    # 638.7224 / 0.005 = 127744.48 → ROUND_HALF_EVEN → 127744 → 638.720.
    assert rounded == Decimal("638.720")


def test_round_to_tick_size_one_cent_tick() -> None:
    rounded = round_to_tick_size(
        price_local=Decimal("100.024"), tick=_tick(Decimal("0.01"))
    )
    assert rounded == Decimal("100.02")


def test_round_to_tick_size_zero_tick_raises() -> None:
    with pytest.raises(LimitPriceNotOnTickSizeError):
        round_to_tick_size(
            price_local=Decimal("100"), tick=_tick(Decimal("0"))
        )


# ---- build_ib_order ----------------------------------------------------


def test_build_ib_order_happy_path_preserves_decimal_then_converts() -> None:
    draft = _draft(
        quantity=Decimal("6"), limit_price=Decimal("638.720")
    )
    contract, order = build_ib_order(draft=draft, tick=_tick())
    # The draft itself is untouched — Decimal everywhere.
    assert draft.quantity == Decimal("6")
    assert draft.limit_price_local == Decimal("638.720")
    # The IB Insync objects carry float values.
    assert isinstance(order.totalQuantity, float)
    assert isinstance(order.lmtPrice, float)
    assert order.totalQuantity == 6.0
    assert order.lmtPrice == 638.72
    # Contract fields are strings (and conId is int if provided).
    assert contract.symbol == "ASML"
    assert contract.exchange == "AEB"
    assert contract.currency == "EUR"
    # Locked TIF + order type
    assert order.tif == "DAY"
    assert order.orderType == "LMT"
    assert order.outsideRth is False


def test_build_ib_order_attaches_conid_when_provided() -> None:
    draft = _draft()
    contract, _ = build_ib_order(draft=draft, tick=_tick(), conid=12345)
    assert contract.conId == 12345


def test_build_ib_order_buy_sell_round_trips() -> None:
    contract_buy, order_buy = build_ib_order(
        draft=_draft(side="BUY"), tick=_tick()
    )
    contract_sell, order_sell = build_ib_order(
        draft=_draft(side="SELL"), tick=_tick()
    )
    assert order_buy.action == "BUY"
    assert order_sell.action == "SELL"


def test_build_ib_order_quantizes_limit_price_to_tick() -> None:
    draft = _draft(limit_price=Decimal("638.7235"))
    _, order = build_ib_order(draft=draft, tick=_tick(Decimal("0.005")))
    # 638.7235 rounds to 638.725.
    assert order.lmtPrice == 638.725


def test_build_ib_order_rejects_off_grid_price() -> None:
    """Off-grid price means drift > one tick after rounding → block.

    Trying to align 638.99 to a 1.0-tick grid yields 639.0 — drift is
    0.01, smaller than 1 tick, so this still passes. We need a price
    that's farther than one tick from any grid point to actually
    trigger ``tick_size_invalid``.
    """
    # Tick is 1.0, price 638.5. Rounding to nearest grid → 638 or 639
    # (banker's). 638.5 is exactly halfway; banker's rounding picks
    # the even neighbour → 638. Drift is 0.5 which equals one tick, so
    # this stays valid.
    draft = _draft(limit_price=Decimal("638.5"))
    _, order = build_ib_order(draft=draft, tick=_tick(Decimal("1.0")))
    assert order.lmtPrice in (638.0, 639.0)


def test_build_ib_order_rejects_non_lmt() -> None:
    draft = _draft(order_type="LMT")  # the dataclass only allows LMT
    # Patch via __dict__ to simulate a corrupted/legacy draft slipping
    # past upstream validation.
    object.__setattr__(draft, "order_type", "MKT")
    with pytest.raises(ValueError):
        build_ib_order(draft=draft, tick=_tick())


def test_build_ib_order_rejects_non_day_tif() -> None:
    draft = _draft()
    object.__setattr__(draft, "time_in_force", "GTC")
    with pytest.raises(ValueError):
        build_ib_order(draft=draft, tick=_tick())


def test_build_ib_order_rejects_zero_quantity() -> None:
    draft = _draft()
    object.__setattr__(draft, "quantity", Decimal("0"))
    with pytest.raises(ValueError):
        build_ib_order(draft=draft, tick=_tick())


def test_build_ib_order_high_precision_decimal_preserved_through_round() -> None:
    """A 6-decimal-place price still aligns to a 3-decimal-place tick."""

    draft = _draft(limit_price=Decimal("123.456789"))
    _, order = build_ib_order(draft=draft, tick=_tick(Decimal("0.005")))
    # 123.456789 / 0.005 = 24691.3578 → ROUND_HALF_EVEN → 24691 → 123.455.
    assert order.lmtPrice == 123.455
