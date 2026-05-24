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
