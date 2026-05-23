from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from portfolio_outlook_api.ibkr_sync_contracts import (
    IbkrCash,
    IbkrExecution,
    IbkrOpenOrder,
    IbkrPosition,
    IbkrReadOnlyAdapter,
)

FIXTURE_TIMESTAMP = datetime(2025, 1, 15, 10, 30, tzinfo=UTC)
TEST_ACCOUNT_REF = "DU_TEST_PAPER"


def build_valid_cash() -> list[IbkrCash]:
    return [
        IbkrCash(
            account_ref=TEST_ACCOUNT_REF,
            base_currency="USD",
            cash=Decimal("1000.25"),
            available_funds=Decimal("800.10"),
            buying_power=Decimal("1600.20"),
        )
    ]


def build_valid_positions() -> list[IbkrPosition]:
    return [
        IbkrPosition(
            account_ref=TEST_ACCOUNT_REF,
            symbol="AAPL",
            security_type="STK",
            currency="USD",
            quantity=Decimal("10"),
            average_cost=Decimal("175.50"),
        )
    ]


def build_valid_open_orders() -> list[IbkrOpenOrder]:
    return [
        IbkrOpenOrder(
            account_ref=TEST_ACCOUNT_REF,
            ibkr_order_id=123,
            ibkr_perm_id=456,
            parent_order_id=None,
            client_id=7,
            symbol="MSFT",
            security_type="STK",
            currency="USD",
            exchange="SMART",
            primary_exchange="NASDAQ",
            action_side="BUY",
            order_type="LMT",
            quantity=Decimal("2"),
            limit_price=Decimal("300.00"),
            stop_price=None,
            tif="DAY",
            status="Submitted",
            filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("2"),
            average_fill_price=None,
            last_status_at=FIXTURE_TIMESTAMP,
            raw_status_reference="fixture-order-1",
        )
    ]


def build_valid_executions() -> list[IbkrExecution]:
    return [
        IbkrExecution(
            account_ref=TEST_ACCOUNT_REF,
            execution_id="EXEC_TEST_1",
            ibkr_order_id=123,
            ibkr_perm_id=456,
            symbol="MSFT",
            security_type="STK",
            currency="USD",
            exchange="SMART",
            primary_exchange="NASDAQ",
            side="BOT",
            quantity=Decimal("1"),
            price=Decimal("299.50"),
            execution_time=FIXTURE_TIMESTAMP,
            commission=Decimal("1.00"),
            commission_currency="USD",
            realized_pnl=Decimal("0"),
            raw_execution_reference="fixture-exec-1",
        )
    ]


class ValidFixtureAdapter(IbkrReadOnlyAdapter):
    def sync_account_summary(self) -> list[IbkrCash]:
        return build_valid_cash()

    def sync_positions(self) -> list[IbkrPosition]:
        return build_valid_positions()

    def sync_open_orders(self) -> list[IbkrOpenOrder]:
        return build_valid_open_orders()

    def sync_executions(self) -> list[IbkrExecution]:
        return build_valid_executions()


class EmptyFixtureAdapter(IbkrReadOnlyAdapter):
    def sync_account_summary(self) -> list[IbkrCash]:
        return []

    def sync_positions(self) -> list[IbkrPosition]:
        return []

    def sync_open_orders(self) -> list[IbkrOpenOrder]:
        return []

    def sync_executions(self) -> list[IbkrExecution]:
        return []


class InvalidFixtureAdapter(ValidFixtureAdapter):
    def sync_positions(self) -> list[IbkrPosition]:
        return [
            IbkrPosition(
                account_ref=TEST_ACCOUNT_REF,
                symbol="MSFT",
                security_type="OPT",
                currency="USD",
                quantity=Decimal("10"),
                average_cost=Decimal("200.50"),
            )
        ]


class TimeoutFixtureAdapter(IbkrReadOnlyAdapter):
    def sync_account_summary(self) -> list[IbkrCash]:
        raise TimeoutError("fixture timeout")

    def sync_positions(self) -> list[IbkrPosition]:
        return []

    def sync_open_orders(self) -> list[IbkrOpenOrder]:
        return []

    def sync_executions(self) -> list[IbkrExecution]:
        return []


class ProviderFailureFixtureAdapter(IbkrReadOnlyAdapter):
    def sync_account_summary(self) -> list[IbkrCash]:
        raise RuntimeError("fixture provider failure")

    def sync_positions(self) -> list[IbkrPosition]:
        return []

    def sync_open_orders(self) -> list[IbkrOpenOrder]:
        return []

    def sync_executions(self) -> list[IbkrExecution]:
        return []
