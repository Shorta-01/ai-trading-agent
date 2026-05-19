from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_outlook_domain.broker_adapter import (
    BrokerAccountModeCheck,
    BrokerAccountModeStatus,
    BrokerCashSnapshot,
    BrokerConnectionSnapshot,
    BrokerConnectionStatus,
    BrokerDataFreshnessStatus,
    BrokerEnvironment,
    BrokerPositionSnapshot,
    BrokerProvider,
)


def test_broker_cash_snapshot_requires_decimal_values() -> None:
    snapshot = BrokerCashSnapshot(
        broker_provider=BrokerProvider.IBKR,
        account_id="U123",
        currency="EUR",
        total_cash_value=Decimal("1000.00"),
        settled_cash=Decimal("800.00"),
        buying_power=Decimal("1200.00"),
        net_liquidation=Decimal("1500.00"),
        source_timestamp=datetime.now(UTC),
        received_at=datetime.now(UTC),
        freshness_status=BrokerDataFreshnessStatus.FRESH,
    )

    assert isinstance(snapshot.total_cash_value, Decimal)
    assert isinstance(snapshot.settled_cash, Decimal)


def test_broker_position_snapshot_rejects_float_values() -> None:
    with pytest.raises(ValueError, match="Float values are not allowed"):
        BrokerPositionSnapshot(
            broker_provider=BrokerProvider.IBKR,
            account_id="U123",
            symbol="IWDA",
            asset_type="ucits_etf",
            currency="EUR",
            quantity=1.5,
            average_cost=Decimal("90.12"),
            source_timestamp=datetime.now(UTC),
            received_at=datetime.now(UTC),
            freshness_status=BrokerDataFreshnessStatus.UNKNOWN,
        )


def test_broker_connection_defaults_block_orders() -> None:
    snapshot = BrokerConnectionSnapshot(
        broker_provider=BrokerProvider.IBKR,
        status=BrokerConnectionStatus.NOT_CONFIGURED,
        checked_at=datetime.now(UTC),
        status_nl="Niet gekoppeld",
        message_nl="Nog geen actieve koppeling.",
    )

    assert snapshot.account_mode_status == BrokerAccountModeStatus.UNKNOWN
    assert snapshot.can_submit_orders is False


def test_account_mode_check_defaults_to_unknown() -> None:
    mode_check = BrokerAccountModeCheck(
        broker_provider=BrokerProvider.IBKR,
        account_id="U123",
        reason_nl="Accountmodus is nog niet gecontroleerd.",
        checked_at=datetime.now(UTC),
    )

    assert mode_check.environment == BrokerEnvironment.UNKNOWN
    assert mode_check.status == BrokerAccountModeStatus.UNKNOWN
    assert mode_check.can_submit_orders is False
