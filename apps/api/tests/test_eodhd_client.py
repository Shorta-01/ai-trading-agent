"""Tests for the EODHD HTTP client.

The HTTP layer is injected via the ``http_fetcher`` callable so these tests
don't make real network calls. We exercise the URL building, the success
path, every documented failure code, and the JSON parser.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_outlook_api.eodhd_client import (
    EodhdAuthError,
    EodhdClient,
    EodhdClientError,
    EodhdHttpResponse,
    EodhdNotFoundError,
    EodhdRateLimitError,
)


def _fetcher_returning(
    *responses: EodhdHttpResponse,
    capture: list[str] | None = None,
) -> Callable[[str, int], EodhdHttpResponse]:
    queued = list(responses)

    def _fetch(url: str, timeout_seconds: int) -> EodhdHttpResponse:
        if capture is not None:
            capture.append(url)
        if not queued:
            raise AssertionError("fetcher called more times than expected")
        return queued.pop(0)

    return _fetch


def _ok(payload: dict[str, object]) -> EodhdHttpResponse:
    return EodhdHttpResponse(status_code=200, body=json.dumps(payload))


def test_fetch_quote_returns_parsed_decimal_fields_and_timestamp() -> None:
    captured: list[str] = []
    client = EodhdClient(
        api_key="test-key",
        base_url="https://example.test/api",
        http_fetcher=_fetcher_returning(
            _ok(
                {
                    "code": "AAPL.US",
                    "timestamp": 1715000000,
                    "gmtoffset": 0,
                    "open": 180.10,
                    "high": 182.20,
                    "low": 179.50,
                    "close": 181.40,
                    "volume": 47000000,
                    "previousClose": 180.00,
                    "change": 1.40,
                    "change_p": 0.78,
                }
            ),
            capture=captured,
        ),
    )

    quote = client.fetch_quote("AAPL.US")

    assert captured == [
        "https://example.test/api/real-time/AAPL.US?api_token=test-key&fmt=json",
    ]
    assert quote.code == "AAPL.US"
    assert quote.last_price == Decimal("181.40")
    assert quote.open_price == Decimal("180.10")
    assert quote.high_price == Decimal("182.20")
    assert quote.low_price == Decimal("179.50")
    assert quote.previous_close == Decimal("180.00")
    assert quote.day_change_percent == Decimal("0.78")
    assert quote.volume == Decimal("47000000")
    assert quote.provider_as_of == datetime.fromtimestamp(1715000000, tz=UTC)


def test_fetch_quote_derives_change_percent_when_missing() -> None:
    client = EodhdClient(
        api_key="k",
        http_fetcher=_fetcher_returning(
            _ok(
                {
                    "code": "ASML.AS",
                    "close": 105.0,
                    "previousClose": 100.0,
                }
            )
        ),
    )

    quote = client.fetch_quote("ASML.AS")

    assert quote.last_price == Decimal("105.0")
    assert quote.previous_close == Decimal("100.0")
    assert quote.day_change_percent == Decimal("5")


def test_fetch_quote_raises_for_empty_symbol() -> None:
    client = EodhdClient(api_key="k", http_fetcher=_fetcher_returning())
    with pytest.raises(EodhdClientError):
        client.fetch_quote("   ")


def test_fetch_quote_raises_auth_error_on_401() -> None:
    client = EodhdClient(
        api_key="k",
        http_fetcher=_fetcher_returning(EodhdHttpResponse(status_code=401, body="unauthorized")),
    )
    with pytest.raises(EodhdAuthError):
        client.fetch_quote("AAPL.US")


def test_fetch_quote_raises_not_found_on_404() -> None:
    client = EodhdClient(
        api_key="k",
        http_fetcher=_fetcher_returning(EodhdHttpResponse(status_code=404, body="not found")),
    )
    with pytest.raises(EodhdNotFoundError):
        client.fetch_quote("UNKNOWN.XX")


def test_fetch_quote_raises_rate_limit_on_429() -> None:
    client = EodhdClient(
        api_key="k",
        http_fetcher=_fetcher_returning(EodhdHttpResponse(status_code=429, body="too many")),
    )
    with pytest.raises(EodhdRateLimitError):
        client.fetch_quote("AAPL.US")


def test_fetch_quote_raises_client_error_on_500() -> None:
    client = EodhdClient(
        api_key="k",
        http_fetcher=_fetcher_returning(EodhdHttpResponse(status_code=500, body="boom")),
    )
    with pytest.raises(EodhdClientError):
        client.fetch_quote("AAPL.US")


def test_fetch_quote_raises_on_invalid_json() -> None:
    client = EodhdClient(
        api_key="k",
        http_fetcher=_fetcher_returning(EodhdHttpResponse(status_code=200, body="not-json")),
    )
    with pytest.raises(EodhdClientError):
        client.fetch_quote("AAPL.US")


def test_fetch_quote_handles_string_numbers() -> None:
    client = EodhdClient(
        api_key="k",
        http_fetcher=_fetcher_returning(
            _ok({"code": "X.US", "close": "12.34", "previousClose": "10.00"})
        ),
    )
    quote = client.fetch_quote("X.US")
    assert quote.last_price == Decimal("12.34")


def test_fetch_quote_returns_none_price_when_missing() -> None:
    client = EodhdClient(
        api_key="k",
        http_fetcher=_fetcher_returning(_ok({"code": "X.US", "close": "NA"})),
    )
    quote = client.fetch_quote("X.US")
    assert quote.last_price is None
    assert quote.day_change_percent is None


def test_fetch_fx_rate_uses_forex_suffix_and_parses_rate() -> None:
    captured: list[str] = []
    client = EodhdClient(
        api_key="k",
        base_url="https://example.test/api",
        http_fetcher=_fetcher_returning(
            _ok(
                {
                    "code": "USDEUR.FOREX",
                    "timestamp": 1715000000,
                    "close": 0.9234,
                    "previousClose": 0.9211,
                }
            ),
            capture=captured,
        ),
    )

    fx = client.fetch_fx_rate("USD", "EUR")

    assert captured == [
        "https://example.test/api/real-time/USDEUR.FOREX?api_token=k&fmt=json",
    ]
    assert fx.base_currency == "USD"
    assert fx.quote_currency == "EUR"
    assert fx.rate == Decimal("0.9234")
    assert fx.previous_close == Decimal("0.9211")
    assert fx.provider_as_of == datetime.fromtimestamp(1715000000, tz=UTC)


def test_fetch_fx_rate_rejects_non_iso_codes() -> None:
    client = EodhdClient(api_key="k", http_fetcher=_fetcher_returning())
    with pytest.raises(EodhdClientError):
        client.fetch_fx_rate("U$", "EUR")
    with pytest.raises(EodhdClientError):
        client.fetch_fx_rate("USD", "EU")


def test_client_rejects_empty_api_key() -> None:
    with pytest.raises(EodhdAuthError):
        EodhdClient(api_key="", http_fetcher=_fetcher_returning())


# ---- fundamentals -----------------------------------------------------


def test_fetch_fundamentals_parses_subset_of_payload() -> None:
    payload = {
        "General": {
            "Code": "AAPL",
            "Sector": "Technology",
            "CurrencyCode": "USD",
        },
        "Highlights": {
            "MarketCapitalization": 3000000000000,
            "PERatio": 30.5,
            "ProfitMargin": 0.25,
            "DividendYield": 0.005,
            "ReturnOnEquityTTM": 1.6,  # fraction form → 160 %
        },
        "Valuation": {
            "TrailingPE": 30.5,
            "PriceBookMRQ": 50.0,
            "EnterpriseValueEbitda": 22.5,
        },
        "Technicals": {
            "52WeekChange": 0.25,  # 25 %
        },
    }
    captured: list[str] = []
    client = EodhdClient(
        api_key="test-key",
        base_url="https://eodhd.example.com/api",
        http_fetcher=_fetcher_returning(_ok(payload), capture=captured),
    )
    result = client.fetch_fundamentals("AAPL.US")
    assert "fundamentals/AAPL.US" in captured[0]
    assert result.eodhd_symbol == "AAPL.US"
    assert result.sector == "Technology"
    assert result.currency == "USD"
    assert result.pe_ratio == Decimal("30.5")
    assert result.pb_ratio == Decimal("50.0")
    assert result.ev_ebitda == Decimal("22.5")
    # ProfitMargin = 0.25 (fraction) → 25 %
    assert result.gross_margin_pct == Decimal("25.00")
    # ROE = 1.6 (already > 1.5 threshold) → kept as percentage
    assert result.roic_pct == Decimal("1.6")
    # Dividend yield 0.005 → 0.5 %
    assert result.dividend_yield_pct == Decimal("0.500")
    # 52WeekChange 0.25 → 25 %
    assert result.return_12m_pct == Decimal("25.00")
    assert result.raw_payload_hash


def test_fetch_fundamentals_tolerates_missing_keys() -> None:
    payload = {"General": {"Code": "MSFT"}}
    client = EodhdClient(
        api_key="test-key",
        http_fetcher=_fetcher_returning(_ok(payload)),
    )
    result = client.fetch_fundamentals("MSFT.US")
    assert result.eodhd_symbol == "MSFT.US"
    assert result.pe_ratio is None
    assert result.pb_ratio is None
    assert result.ev_ebitda is None
    assert result.sector is None
    assert result.raw_payload_hash


def test_fetch_fundamentals_rejects_non_object_payload() -> None:
    client = EodhdClient(
        api_key="test-key",
        http_fetcher=_fetcher_returning(EodhdHttpResponse(status_code=200, body="[]")),
    )
    with pytest.raises(EodhdClientError):
        client.fetch_fundamentals("AAPL.US")


def test_fetch_fundamentals_rejects_empty_symbol() -> None:
    client = EodhdClient(
        api_key="test-key",
        http_fetcher=_fetcher_returning(),
    )
    with pytest.raises(EodhdClientError):
        client.fetch_fundamentals("")
