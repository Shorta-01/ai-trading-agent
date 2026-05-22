from portfolio_outlook_domain.market_data_foundation import (
    MarketDataFetchStatus,
    MarketDataIdentity,
    block_if_identity_invalid,
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
    assert MarketDataFetchStatus.SNAPSHOT_AVAILABLE.value == "snapshot_available"
    assert MarketDataFetchStatus.PROVIDER_NOT_CONFIGURED.value == "provider_not_configured"


def test_block_if_identity_with_whitespace_conid_is_missing() -> None:
    result = block_if_identity_invalid(
        MarketDataIdentity(ibkr_conid="   ", identity_validated=True)
    )
    assert result is not None
    assert result.status is MarketDataFetchStatus.MISSING_IDENTITY
    assert "Contract ontbreekt" in result.message_nl


def test_block_if_identity_not_validated_contains_dutch_blocked_message() -> None:
    result = block_if_identity_invalid(
        MarketDataIdentity(ibkr_conid="456", identity_validated=False)
    )
    assert result is not None
    assert result.status is MarketDataFetchStatus.IDENTITY_NOT_VALIDATED
    assert "geblokkeerd" in result.message_nl.lower()
