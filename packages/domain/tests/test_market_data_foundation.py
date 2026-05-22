from datetime import UTC, datetime, timedelta
from decimal import Decimal

from portfolio_outlook_domain.market_data_foundation import (
    MarketDataFetchStatus,
    MarketDataFreshnessStatus,
    MarketDataIdentity,
    MarketDataPriceBasis,
    MarketDataReadinessPolicy,
    MarketDataSnapshot,
    MarketDataValuationReadinessStatus,
    block_if_identity_invalid,
    evaluate_market_data_readiness,
)


def test_block_if_identity_missing_conid() -> None:
    result = block_if_identity_invalid(MarketDataIdentity(ibkr_conid="", identity_validated=True))
    assert result is not None
    assert result.status is MarketDataFetchStatus.MISSING_IDENTITY


def test_block_if_identity_not_validated() -> None:
    result = block_if_identity_invalid(
        MarketDataIdentity(ibkr_conid="123", identity_validated=False)
    )
    assert result is not None
    assert result.status is MarketDataFetchStatus.IDENTITY_NOT_VALIDATED


def test_identity_ok_returns_none() -> None:
    assert (
        block_if_identity_invalid(MarketDataIdentity(ibkr_conid="123", identity_validated=True))
        is None
    )


def test_market_data_fetch_status_contains_storage_and_stale_variants() -> None:
    assert MarketDataFetchStatus.STORAGE_ERROR.value == "storage_error"
    assert MarketDataFetchStatus.STALE_SNAPSHOT.value == "stale_snapshot"


def test_block_if_identity_with_whitespace_conid_is_missing() -> None:
    result = block_if_identity_invalid(
        MarketDataIdentity(ibkr_conid="   ", identity_validated=True)
    )
    assert result is not None
    assert result.status is MarketDataFetchStatus.MISSING_IDENTITY


def test_block_if_identity_not_validated_contains_dutch_blocked_message() -> None:
    result = block_if_identity_invalid(
        MarketDataIdentity(ibkr_conid="456", identity_validated=False)
    )
    assert result is not None
    assert result.status is MarketDataFetchStatus.IDENTITY_NOT_VALIDATED


def _snapshot(
    *, received_at: datetime, last: Decimal | None, bid: Decimal | None, ask: Decimal | None
) -> MarketDataSnapshot:
    return MarketDataSnapshot(
        ibkr_conid="1",
        symbol="AAPL",
        currency="USD",
        requested_at=received_at,
        received_at=received_at,
        provider_as_of=received_at,
        stored_at=received_at,
        provider_code="ibkr",
        provider_environment="paper",
        provider_account_mode="paper",
        data_domain="market_data",
        request_kind="snapshot",
        source_type="manual",
        last_price=last,
        bid_price=bid,
        ask_price=ask,
        day_change_percent=None,
    )


def test_readiness_missing_snapshot_blocked() -> None:
    now = datetime(2026, 5, 22, tzinfo=UTC)
    result = evaluate_market_data_readiness(
        snapshot=None, now=now, policy=MarketDataReadinessPolicy()
    )
    assert (
        result.valuation_readiness_status
        is MarketDataValuationReadinessStatus.BLOCKED_MISSING_SNAPSHOT
    )


def test_readiness_fresh_last_price_ready() -> None:
    now = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)
    snap = _snapshot(
        received_at=now - timedelta(minutes=5),
        last=Decimal("10.10"),
        bid=None,
        ask=None,
    )
    result = evaluate_market_data_readiness(
        snapshot=snap, now=now, policy=MarketDataReadinessPolicy()
    )
    assert result.freshness_status is MarketDataFreshnessStatus.FRESH
    assert (
        result.valuation_readiness_status
        is MarketDataValuationReadinessStatus.READY_FOR_VALUATION_PREVIEW
    )
    assert result.price_basis is MarketDataPriceBasis.LAST


def test_readiness_stale_blocks_valuation() -> None:
    now = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)
    snap = _snapshot(
        received_at=now - timedelta(hours=2),
        last=Decimal("10.10"),
        bid=None,
        ask=None,
    )
    result = evaluate_market_data_readiness(
        snapshot=snap, now=now, policy=MarketDataReadinessPolicy()
    )
    assert (
        result.valuation_readiness_status
        is MarketDataValuationReadinessStatus.BLOCKED_STALE_SNAPSHOT
    )
