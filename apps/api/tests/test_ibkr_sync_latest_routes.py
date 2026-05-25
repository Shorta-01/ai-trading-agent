"""Task 126b — ``GET /ibkr/sync/positions/latest`` + ``/cash/latest`` tests.

Acceptance criterion #11: Decimal preservation end-to-end —
``quantity=Decimal("12.5")`` + ``avg_cost=Decimal("640.123456")``
makes it from the worker storage row through the API JSON response
without precision loss.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from ai_trading_agent_storage import (
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    StorageConnectionError,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api.ibkr_connection_read_model import LatestSyncReadResult
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_BASE_TIME = datetime(2026, 5, 25, 12, 0, 0, tzinfo=UTC)


def _reset_settings() -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.ibkr_account_id_hint = "DU1234567"


def setup_function() -> None:
    _reset_settings()


def teardown_function() -> None:
    api_settings.ibkr_account_id_hint = None
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None


def _patch_sync_payload(payload: LatestSyncReadResult) -> Any:
    def _fake(storage: object) -> LatestSyncReadResult:  # noqa: ARG001
        return payload

    return patch(
        "portfolio_outlook_api.ibkr_connection_routes.read_latest_sync_payload",
        side_effect=_fake,
    )


def _position(
    *,
    symbol: str = "AAPL",
    quantity: Decimal = Decimal("100"),
    avg_cost: Decimal | None = Decimal("135.45"),
    ibkr_account_id: str | None = "DU1234567",
) -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id=f"pos-{symbol}",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        conid="265598",
        symbol=symbol,
        security_type="STK",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        quantity=quantity,
        average_cost=avg_cost,
        received_at=_BASE_TIME,
        stored_at=_BASE_TIME,
        ibkr_account_id=ibkr_account_id,
    )


def _cash(
    *,
    base_currency: str = "EUR",
    cash: Decimal | None = Decimal("12345.67"),
    available_funds: Decimal | None = Decimal("11000.00"),
    buying_power: Decimal | None = Decimal("44000.00"),
    ibkr_account_id: str | None = "DU1234567",
) -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id=f"cash-{base_currency}",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        base_currency=base_currency,
        cash=cash,
        available_funds=available_funds,
        buying_power=buying_power,
        received_at=_BASE_TIME,
        stored_at=_BASE_TIME,
        ibkr_account_id=ibkr_account_id,
    )


# ---- positions ---------------------------------------------------


def test_positions_route_returns_locked_v126b_shape() -> None:
    payload = LatestSyncReadResult(
        sync_run_id="sync-1",
        received_at=_BASE_TIME,
        positions=(_position(),),
        cash_rows=tuple(),
    )
    with _patch_sync_payload(payload):
        body = client.get("/ibkr/sync/positions/latest").json()

    assert body["sync_run_id"] == "sync-1"
    assert body["as_of"] == _BASE_TIME.isoformat()
    assert body["safe_for_orders"] is False
    assert len(body["items"]) == 1
    row = body["items"][0]
    assert row["symbol"] == "AAPL"
    assert row["exchange"] == "SMART"
    assert row["ibkr_account_id"] == "DU•••4567"
    assert row["currency"] == "USD"
    assert row["quantity"] == "100"
    assert row["avg_cost"] == "135.45"
    # Fields not yet populated by the worker default to null.
    assert row["market_price"] is None
    assert row["market_value"] is None
    assert row["unrealized_pnl"] is None


def test_positions_route_preserves_six_decimal_precision_end_to_end() -> None:
    """Acceptance criterion #11: Decimal round-trip through JSON."""

    payload = LatestSyncReadResult(
        sync_run_id="sync-1",
        received_at=_BASE_TIME,
        positions=(
            _position(
                symbol="MSFT",
                quantity=Decimal("12.5"),
                avg_cost=Decimal("640.123456"),
            ),
        ),
        cash_rows=tuple(),
    )
    with _patch_sync_payload(payload):
        body = client.get("/ibkr/sync/positions/latest").json()
    row = body["items"][0]
    # JSON strings, then round-tripped through Decimal.
    assert Decimal(row["quantity"]) == Decimal("12.5")
    assert Decimal(row["avg_cost"]) == Decimal("640.123456")
    # Verify the raw string carries the trailing precision.
    assert row["avg_cost"] == "640.123456"


def test_positions_route_returns_empty_items_when_no_sync_run() -> None:
    payload = LatestSyncReadResult(
        sync_run_id=None,
        received_at=None,
        positions=tuple(),
        cash_rows=tuple(),
    )
    with _patch_sync_payload(payload):
        body = client.get("/ibkr/sync/positions/latest").json()
    assert body["items"] == []
    assert body["sync_run_id"] is None
    assert body["as_of"] is None


def test_positions_route_returns_503_with_dutch_body_when_storage_unavailable() -> None:
    with patch(
        "portfolio_outlook_api.ibkr_connection_routes.read_latest_sync_payload",
        side_effect=StorageConnectionError("down"),
    ):
        response = client.get("/ibkr/sync/positions/latest")
    assert response.status_code == 503
    assert response.json() == {"detail": "Opslag is niet beschikbaar."}


# ---- cash --------------------------------------------------------


def test_cash_route_returns_locked_v126b_shape() -> None:
    payload = LatestSyncReadResult(
        sync_run_id="sync-1",
        received_at=_BASE_TIME,
        positions=tuple(),
        cash_rows=(_cash(), _cash(base_currency="USD", cash=Decimal("500.00"))),
    )
    with _patch_sync_payload(payload):
        body = client.get("/ibkr/sync/cash/latest").json()

    assert body["sync_run_id"] == "sync-1"
    assert body["as_of"] == _BASE_TIME.isoformat()
    assert len(body["items"]) == 2
    eur_row = body["items"][0]
    assert eur_row["currency"] == "EUR"
    assert eur_row["cash"] == "12345.67"
    assert eur_row["available_funds"] == "11000.00"
    assert eur_row["buying_power"] == "44000.00"
    assert eur_row["ibkr_account_id"] == "DU•••4567"
    # Fields not yet populated default to null.
    assert eur_row["net_liquidation_value"] is None
    assert eur_row["total_cash_value"] is None


def test_cash_route_preserves_decimal_precision_end_to_end() -> None:
    payload = LatestSyncReadResult(
        sync_run_id="sync-1",
        received_at=_BASE_TIME,
        positions=tuple(),
        cash_rows=(
            _cash(
                cash=Decimal("99999.999999"),
                available_funds=Decimal("12345.678901"),
            ),
        ),
    )
    with _patch_sync_payload(payload):
        row = client.get("/ibkr/sync/cash/latest").json()["items"][0]
    assert row["cash"] == "99999.999999"
    assert row["available_funds"] == "12345.678901"


def test_cash_route_returns_503_with_dutch_body_when_storage_unavailable() -> None:
    with patch(
        "portfolio_outlook_api.ibkr_connection_routes.read_latest_sync_payload",
        side_effect=StorageConnectionError("down"),
    ):
        response = client.get("/ibkr/sync/cash/latest")
    assert response.status_code == 503
    assert response.json() == {"detail": "Opslag is niet beschikbaar."}
