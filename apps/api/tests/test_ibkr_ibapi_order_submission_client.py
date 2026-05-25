"""Tests for the real ``ibapi`` order-submission client.

Drives the production callback set via an injected fake app so the test
exercises real parsing / state-mutation paths without opening a socket.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from portfolio_outlook_api.ibkr_ibapi_order_submission_client import (
    IbapiOrderSubmissionClient,
    OrderSubmissionInputs,
    build_contract_and_order,
    build_contract_and_orders,
    build_submission_callbacks,
)


class _FakeIbapiApp:
    """Fake app that synchronously forwards request calls to production
    callbacks (which we install via ``attach_callbacks``)."""

    def __init__(
        self,
        *,
        connected_after_connect: bool = True,
        next_valid_id_value: int | None = 1234,
        open_order_perm_id: int = 9999,
        order_status_text: str = "Submitted",
        rejected_reason_from_error: tuple[int, str] | None = None,
    ) -> None:
        self.connected = False
        self.connected_after_connect = connected_after_connect
        self.next_valid_id_value = next_valid_id_value
        self.open_order_perm_id = open_order_perm_id
        self.order_status_text = order_status_text
        self.rejected_reason_from_error = rejected_reason_from_error
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.req_ids_calls = 0
        self.placed_orders: list[tuple[int, object, object]] = []
        self._cb: dict[str, Any] = {}

    def attach_callbacks(self, callbacks: dict[str, Any]) -> None:
        self._cb = callbacks

    def connect(self, host: str, port: int, client_id: int) -> None:
        self.connect_calls += 1
        self.connected = self.connected_after_connect

    def isConnected(self) -> bool:  # noqa: N802
        return self.connected

    def disconnect(self) -> None:
        self.disconnect_calls += 1
        self.connected = False

    def run(self) -> None:
        return None

    def reqIds(self, num_ids: int) -> None:  # noqa: N802
        self.req_ids_calls += 1
        if self.next_valid_id_value is not None:
            self._cb["nextValidId"](self, self.next_valid_id_value)

    def placeOrder(  # noqa: N802
        self, order_id: int, contract: object, order: object
    ) -> None:
        self.placed_orders.append((order_id, contract, order))
        if self.rejected_reason_from_error is not None:
            code, message = self.rejected_reason_from_error
            self._cb["error"](self, order_id, code, message)
            return

        class _OrderState:
            status = self.order_status_text

        class _SyntheticOrder:
            permId = self.open_order_perm_id

        self._cb["openOrder"](self, order_id, contract, _SyntheticOrder(), _OrderState())


def _make_client(
    fake: _FakeIbapiApp,
    *,
    timeout_seconds: int = 5,
    contract_builder=None,  # type: ignore[no-untyped-def]
) -> IbapiOrderSubmissionClient:
    client = IbapiOrderSubmissionClient(
        host="127.0.0.1",
        port=4002,
        client_id=11,
        timeout_seconds=timeout_seconds,
        provider_code="ibkr",
        app=fake,
        contract_order_builder=contract_builder or (lambda inputs: (object(), object())),
    )
    fake.attach_callbacks(build_submission_callbacks(client._state, client._lock))
    return client


def _inputs(**overrides) -> OrderSubmissionInputs:  # type: ignore[no-untyped-def]
    base = dict(
        symbol="AAPL",
        primary_exchange="NASDAQ",
        currency="USD",
        security_type="STK",
        action_side="BUY",
        quantity=Decimal("5"),
        limit_price=Decimal("180"),
    )
    base.update(overrides)
    return OrderSubmissionInputs(**base)


def test_happy_path_captures_order_id_and_perm_id() -> None:
    fake = _FakeIbapiApp(next_valid_id_value=1234, open_order_perm_id=987654)
    client = _make_client(fake)
    try:
        result = client.submit(_inputs())
    finally:
        client.close()

    assert result.accepted is True
    assert result.ibkr_order_id == 1234
    assert result.ibkr_perm_id == 987654
    assert result.ibkr_status_text == "Submitted"
    assert fake.placed_orders[0][0] == 1234
    assert fake.disconnect_calls == 1


def test_returns_blocked_when_next_valid_id_never_arrives() -> None:
    fake = _FakeIbapiApp(next_valid_id_value=None)
    client = _make_client(fake, timeout_seconds=1)
    try:
        result = client.submit(_inputs())
    finally:
        client.close()

    assert result.accepted is False
    assert result.rejected_reason == "next_valid_id_timeout"


def test_returns_rejected_when_ibapi_error_fires_during_place_order() -> None:
    fake = _FakeIbapiApp(rejected_reason_from_error=(201, "Order rejected"))
    client = _make_client(fake)
    try:
        result = client.submit(_inputs())
    finally:
        client.close()

    assert result.accepted is False
    assert result.rejected_reason is not None
    assert "201" in result.rejected_reason


def test_close_is_idempotent() -> None:
    fake = _FakeIbapiApp()
    client = _make_client(fake)
    client.submit(_inputs())
    client.close()
    client.close()  # second close must not raise
    assert fake.disconnect_calls == 1


# ---- build_contract_and_order input validation ---------------------------


def test_build_contract_and_order_rejects_non_stk_security_type() -> None:
    with pytest.raises(ValueError):
        build_contract_and_order(_inputs(security_type="OPT"))


def test_build_contract_and_order_rejects_non_whole_quantity() -> None:
    with pytest.raises(ValueError):
        build_contract_and_order(_inputs(quantity=Decimal("2.5")))


def test_build_contract_and_order_rejects_non_positive_price() -> None:
    with pytest.raises(ValueError):
        build_contract_and_order(_inputs(limit_price=Decimal("0")))


def test_build_contract_and_order_rejects_unknown_action_side() -> None:
    with pytest.raises(ValueError):
        build_contract_and_order(_inputs(action_side="SHORT"))


# ---- §21.3 order vocabulary (Slice 20) -----------------------------------


def test_build_lmt_sets_orderType_and_lmtPrice() -> None:
    _, order = build_contract_and_order(_inputs(order_type="LMT", limit_price=Decimal("180")))
    assert order.orderType == "LMT"
    assert order.lmtPrice == Decimal("180")
    assert order.tif == "DAY"
    assert order.transmit is True


def test_build_mkt_sets_orderType_market() -> None:
    _, order = build_contract_and_order(
        _inputs(order_type="MKT", limit_price=Decimal("180"))
    )
    assert order.orderType == "MKT"
    assert order.action == "BUY"
    assert order.transmit is True
    # ibapi's Order initialises auxPrice and lmtPrice to a sentinel
    # max-float; the client does not overwrite them for MKT.


def test_build_stp_sets_orderType_stop_and_auxPrice() -> None:
    _, order = build_contract_and_order(
        _inputs(
            order_type="STP",
            action_side="SELL",
            limit_price=Decimal("180"),
            stop_price=Decimal("170"),
        )
    )
    assert order.orderType == "STP"
    assert order.auxPrice == Decimal("170")


def test_build_stp_rejects_missing_stop_price() -> None:
    with pytest.raises(ValueError, match="stop_price"):
        build_contract_and_order(_inputs(order_type="STP", stop_price=None))


def test_build_stp_lmt_sets_orderType_stop_limit_and_both_prices() -> None:
    _, order = build_contract_and_order(
        _inputs(
            order_type="STP_LMT",
            action_side="SELL",
            limit_price=Decimal("178"),
            stop_price=Decimal("180"),
        )
    )
    assert order.orderType == "STP LMT"
    assert order.auxPrice == Decimal("180")
    assert order.lmtPrice == Decimal("178")


def test_build_trail_with_amount_sets_auxPrice() -> None:
    _, order = build_contract_and_order(
        _inputs(
            order_type="TRAIL",
            action_side="SELL",
            limit_price=Decimal("180"),
            trail_amount=Decimal("2"),
        )
    )
    assert order.orderType == "TRAIL"
    assert order.auxPrice == Decimal("2")


def test_build_trail_with_percent_sets_trailingPercent() -> None:
    _, order = build_contract_and_order(
        _inputs(
            order_type="TRAIL",
            action_side="SELL",
            limit_price=Decimal("180"),
            trail_percent=Decimal("1.5"),
        )
    )
    assert order.orderType == "TRAIL"
    assert order.trailingPercent == Decimal("1.5")


def test_build_trail_rejects_both_amount_and_percent() -> None:
    with pytest.raises(ValueError, match="trail_amount"):
        build_contract_and_order(
            _inputs(
                order_type="TRAIL",
                trail_amount=Decimal("1"),
                trail_percent=Decimal("1"),
            )
        )


def test_build_trail_lmt_sets_orderType_trail_limit_and_lmtPrice() -> None:
    _, order = build_contract_and_order(
        _inputs(
            order_type="TRAIL_LMT",
            action_side="SELL",
            limit_price=Decimal("178"),
            trail_amount=Decimal("2"),
        )
    )
    assert order.orderType == "TRAIL LIMIT"
    assert order.auxPrice == Decimal("2")
    assert order.lmtPrice == Decimal("178")


def test_build_bracket_returns_three_orders_with_correct_transmit_flags() -> None:
    _, orders = build_contract_and_orders(
        _inputs(
            order_type="BRACKET",
            action_side="BUY",
            limit_price=Decimal("100"),
            bracket_take_profit_limit_price=Decimal("110"),
            bracket_stop_loss_price=Decimal("95"),
        )
    )
    assert len(orders) == 3
    parent, tp, sl = orders
    assert parent.orderType == "LMT"
    assert parent.lmtPrice == Decimal("100")
    assert parent.action == "BUY"
    assert parent.transmit is False

    assert tp.orderType == "LMT"
    assert tp.action == "SELL"
    assert tp.lmtPrice == Decimal("110")
    assert tp.transmit is False

    assert sl.orderType == "STP"
    assert sl.action == "SELL"
    assert sl.auxPrice == Decimal("95")
    assert sl.transmit is True


def test_build_bracket_sell_inverts_child_sides() -> None:
    _, orders = build_contract_and_orders(
        _inputs(
            order_type="BRACKET",
            action_side="SELL",
            limit_price=Decimal("100"),
            bracket_take_profit_limit_price=Decimal("90"),
            bracket_stop_loss_price=Decimal("110"),
        )
    )
    parent, tp, sl = orders
    assert parent.action == "SELL"
    assert tp.action == "BUY"
    assert sl.action == "BUY"


def test_build_contract_and_order_rejects_bracket() -> None:
    with pytest.raises(ValueError, match="BRACKET"):
        build_contract_and_order(
            _inputs(
                order_type="BRACKET",
                action_side="BUY",
                limit_price=Decimal("100"),
                bracket_take_profit_limit_price=Decimal("110"),
                bracket_stop_loss_price=Decimal("95"),
            )
        )


def test_build_rejects_unsupported_order_type() -> None:
    with pytest.raises(ValueError, match="order_type"):
        build_contract_and_orders(_inputs(order_type="MOC"))


def test_submit_bracket_places_three_orders_with_parent_id_chain() -> None:
    fake = _FakeIbapiApp(next_valid_id_value=500, open_order_perm_id=11)
    client = _make_client(
        fake,
        contract_builder=None,
    )
    # Inject the real multi-order builder via the keyword-only argument.
    # We rebuild the client with the multi-order injector so BRACKET works.
    client.close()

    captured: dict[str, Any] = {}

    def _multi_builder(inputs: OrderSubmissionInputs) -> tuple[Any, list[Any]]:
        class _O:
            def __init__(self) -> None:
                self.parentId = 0

        parent = _O()
        tp = _O()
        sl = _O()
        captured["orders"] = [parent, tp, sl]
        return object(), [parent, tp, sl]

    fake2 = _FakeIbapiApp(next_valid_id_value=500, open_order_perm_id=11)
    client = IbapiOrderSubmissionClient(
        host="127.0.0.1",
        port=4002,
        client_id=11,
        timeout_seconds=5,
        provider_code="ibkr",
        app=fake2,
        contract_orders_builder=_multi_builder,
    )
    fake2.attach_callbacks(build_submission_callbacks(client._state, client._lock))
    try:
        result = client.submit(
            _inputs(
                order_type="BRACKET",
                action_side="BUY",
                limit_price=Decimal("100"),
                bracket_take_profit_limit_price=Decimal("110"),
                bracket_stop_loss_price=Decimal("95"),
            )
        )
    finally:
        client.close()

    assert result.accepted is True
    assert result.ibkr_order_id == 500
    # Parent at 500, TP at 501, SL at 502.
    assert [oid for oid, _, _ in fake2.placed_orders] == [500, 501, 502]
    # Children should carry parentId = parent's order_id.
    _, tp, sl = captured["orders"]
    assert tp.parentId == 500
    assert sl.parentId == 500
