"""Tests for the EODHD historical-bars endpoint of ``EodhdClient``."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from portfolio_outlook_api.eodhd_client import (
    EodhdClient,
    EodhdClientError,
    EodhdHttpResponse,
    EodhdNotFoundError,
)


def _ok(payload: object) -> EodhdHttpResponse:
    return EodhdHttpResponse(status_code=200, body=json.dumps(payload))


def test_fetch_eod_bars_returns_chronologically_sorted_typed_bars() -> None:
    captured: list[str] = []

    def fetcher(url: str, _t: int) -> EodhdHttpResponse:
        captured.append(url)
        return _ok(
            [
                {
                    "date": "2025-01-03",
                    "open": 102.0,
                    "high": 103.5,
                    "low": 101.5,
                    "close": 103.0,
                    "adjusted_close": 103.0,
                    "volume": 1500000,
                },
                {
                    "date": "2025-01-02",
                    "open": 101.0,
                    "high": 102.5,
                    "low": 100.5,
                    "close": 102.0,
                    "adjusted_close": 102.0,
                    "volume": 1200000,
                },
                {
                    "date": "2025-01-06",
                    "open": 103.0,
                    "high": 104.0,
                    "low": 102.5,
                    "close": 103.8,
                    "adjusted_close": 103.8,
                    "volume": 1800000,
                },
            ]
        )

    client = EodhdClient(
        api_key="k",
        base_url="https://example.test/api",
        http_fetcher=fetcher,
    )

    bars = client.fetch_eod_bars(
        "AAPL.US", from_date=date(2025, 1, 1), to_date=date(2025, 1, 10)
    )

    assert (
        captured[0]
        == "https://example.test/api/eod/AAPL.US?api_token=k&fmt=json"
        "&from=2025-01-01&to=2025-01-10&period=d"
    )
    assert [b.bar_date for b in bars] == [
        date(2025, 1, 2),
        date(2025, 1, 3),
        date(2025, 1, 6),
    ]
    assert bars[0].close_price == Decimal("102.0")
    assert bars[1].close_price == Decimal("103.0")
    assert bars[2].volume == Decimal("1800000")


def test_fetch_eod_bars_filters_invalid_or_missing_date_rows() -> None:
    def fetcher(_url: str, _t: int) -> EodhdHttpResponse:
        return _ok(
            [
                {"date": "2025-01-02", "close": 100.0},
                {"date": "", "close": 99.0},  # filtered
                {"date": "not-a-date", "close": 98.0},  # filtered
                "garbage",  # not a dict
                {"date": "2025-01-03", "close": 101.0},
            ]
        )

    client = EodhdClient(api_key="k", http_fetcher=fetcher)
    bars = client.fetch_eod_bars(
        "AAPL.US", from_date=date(2025, 1, 1), to_date=date(2025, 1, 10)
    )

    assert [b.bar_date for b in bars] == [date(2025, 1, 2), date(2025, 1, 3)]


def test_fetch_eod_bars_raises_when_response_is_not_array() -> None:
    client = EodhdClient(
        api_key="k",
        http_fetcher=lambda _u, _t: _ok({"unexpected": "object"}),
    )
    with pytest.raises(EodhdClientError):
        client.fetch_eod_bars(
            "AAPL.US", from_date=date(2025, 1, 1), to_date=date(2025, 1, 10)
        )


def test_fetch_eod_bars_raises_on_inverted_date_range() -> None:
    client = EodhdClient(api_key="k", http_fetcher=lambda _u, _t: _ok([]))
    with pytest.raises(EodhdClientError):
        client.fetch_eod_bars(
            "AAPL.US", from_date=date(2025, 1, 10), to_date=date(2025, 1, 5)
        )


def test_fetch_eod_bars_propagates_provider_errors() -> None:
    client = EodhdClient(
        api_key="k",
        http_fetcher=lambda _u, _t: EodhdHttpResponse(status_code=404, body="nope"),
    )
    with pytest.raises(EodhdNotFoundError):
        client.fetch_eod_bars(
            "MYSTERY.XX", from_date=date(2025, 1, 1), to_date=date(2025, 1, 10)
        )


def test_fetch_eod_bars_rejects_empty_symbol() -> None:
    client = EodhdClient(api_key="k", http_fetcher=lambda _u, _t: _ok([]))
    with pytest.raises(EodhdClientError):
        client.fetch_eod_bars(
            "   ", from_date=date(2025, 1, 1), to_date=date(2025, 1, 10)
        )
