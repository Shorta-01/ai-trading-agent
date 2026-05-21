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
