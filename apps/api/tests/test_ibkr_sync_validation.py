from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal

from portfolio_outlook_api.ibkr_sync_contracts import (
    IbkrCash,
    IbkrExecution,
    IbkrOpenOrder,
    IbkrPosition,
)
from portfolio_outlook_api.ibkr_sync_validation import validate_ibkr_sync_payloads


def _valid_payloads():
    return (
        [IbkrCash("paper", "USD", Decimal("10"), Decimal("8"), Decimal("20"))],
        [IbkrPosition("paper", "MSFT", "STK", "USD", Decimal("1"), Decimal("10"))],
        [
            IbkrOpenOrder(
                "paper",
                1,
                None,
                None,
                None,
                "MSFT",
                "STK",
                "USD",
                None,
                None,
                "BUY",
                "LMT",
                Decimal("1"),
                Decimal("10"),
                None,
                "DAY",
                "Submitted",
                Decimal("0"),
                Decimal("1"),
                None,
                datetime.now(UTC),
                None,
            )
        ],
        [
            IbkrExecution(
                "paper",
                "E1",
                1,
                None,
                "MSFT",
                "STK",
                "USD",
                None,
                None,
                "BOT",
                Decimal("1"),
                Decimal("10"),
                datetime.now(UTC),
                None,
                None,
                None,
                None,
            )
        ],
    )


def test_validation_passes_with_valid_payloads() -> None:
    result = validate_ibkr_sync_payloads(*_valid_payloads())
    assert result.passed is True
    assert result.errors == []


def test_invalid_cash_payload_fails() -> None:
    cash, positions, orders, execs = _valid_payloads()
    cash[0] = IbkrCash("", "usd", Decimal("1"), None, None)
    result = validate_ibkr_sync_payloads(cash, positions, orders, execs)
    assert result.passed is False
    assert any(e.payload_kind == "cash" for e in result.errors)


def test_invalid_position_payload_fails() -> None:
    cash, positions, orders, execs = _valid_payloads()
    positions[0] = IbkrPosition("paper", "", "OPT", "US", Decimal("-1"), Decimal("-2"))
    result = validate_ibkr_sync_payloads(cash, positions, orders, execs)
    assert result.passed is False
    assert any(e.payload_kind == "position" for e in result.errors)


def test_invalid_open_order_payload_fails() -> None:
    cash, positions, orders, execs = _valid_payloads()
    orders[0] = IbkrOpenOrder(
        "paper",
        -1,
        None,
        None,
        None,
        "",
        "STK",
        "usd",
        None,
        None,
        "HOLD",
        "",
        Decimal("0"),
        Decimal("0"),
        None,
        "DAY",
        "",
        Decimal("-1"),
        Decimal("-1"),
        None,
        datetime.now(UTC),
        None,
    )
    result = validate_ibkr_sync_payloads(cash, positions, orders, execs)
    assert result.passed is False
    assert any(e.payload_kind == "open_order" for e in result.errors)


def test_invalid_execution_payload_fails() -> None:
    cash, positions, orders, execs = _valid_payloads()
    execs[0] = IbkrExecution(
        "",
        "",
        0,
        None,
        "",
        "STK",
        "usd",
        None,
        None,
        "X",
        Decimal("0"),
        Decimal("0"),
        "bad",
        None,
        None,
        None,
        None,
    )  # type: ignore[arg-type]
    result = validate_ibkr_sync_payloads(cash, positions, orders, execs)
    assert result.passed is False
    assert any(e.payload_kind == "execution" for e in result.errors)


def test_unsupported_security_and_duplicates_fail() -> None:
    cash, positions, orders, execs = _valid_payloads()
    positions.append(IbkrPosition("paper", "MSFT", "OPT", "USD", Decimal("1"), Decimal("1")))
    orders.append(orders[0])
    execs.append(execs[0])
    result = validate_ibkr_sync_payloads(cash, positions, orders, execs)
    assert any(e.reason_code == "unsupported_security_type" for e in result.errors)
    assert any(e.reason_code == "duplicate_order_id" for e in result.errors)
    assert any(e.reason_code == "duplicate_execution_id" for e in result.errors)


def test_validator_does_not_mutate_inputs() -> None:
    payloads = _valid_payloads()
    original = deepcopy(payloads)
    validate_ibkr_sync_payloads(*payloads)
    assert payloads == original
