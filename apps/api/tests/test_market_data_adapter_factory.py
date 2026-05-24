"""Tests for the market-data provider factory.

The factory must return ``None`` for every disabled or unconfigured gate,
and a real ``EodhdClient`` only when every gate passes.
"""

from __future__ import annotations

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.eodhd_client import EodhdClient, EodhdHttpResponse
from portfolio_outlook_api.market_data_adapter_factory import build_market_data_provider


def _ready_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "market_data_sync_enabled": True,
        "market_data_provider": "eodhd",
        "eodhd_enabled": True,
        "eodhd_api_key": "test-key",
        "eodhd_base_url": "https://example.test/api",
        "eodhd_request_timeout_seconds": 5,
    }
    values.update(overrides)
    return Settings(**values)


def _noop_fetcher(url: str, timeout_seconds: int) -> EodhdHttpResponse:
    return EodhdHttpResponse(status_code=200, body="{}")


def test_factory_returns_eodhd_client_when_fully_configured() -> None:
    provider = build_market_data_provider(_ready_settings(), http_fetcher=_noop_fetcher)
    assert isinstance(provider, EodhdClient)


def test_factory_returns_none_when_sync_disabled() -> None:
    settings = _ready_settings(market_data_sync_enabled=False)
    assert build_market_data_provider(settings, http_fetcher=_noop_fetcher) is None


def test_factory_returns_none_for_unknown_provider() -> None:
    settings = _ready_settings(market_data_provider="polygon")
    assert build_market_data_provider(settings, http_fetcher=_noop_fetcher) is None


def test_factory_returns_none_when_eodhd_disabled() -> None:
    settings = _ready_settings(eodhd_enabled=False)
    assert build_market_data_provider(settings, http_fetcher=_noop_fetcher) is None


def test_factory_returns_none_when_api_key_missing() -> None:
    settings = _ready_settings(eodhd_api_key=None)
    assert build_market_data_provider(settings, http_fetcher=_noop_fetcher) is None


def test_factory_returns_none_when_api_key_empty() -> None:
    settings = _ready_settings(eodhd_api_key="")
    assert build_market_data_provider(settings, http_fetcher=_noop_fetcher) is None


def test_factory_is_case_insensitive_on_provider_name() -> None:
    settings = _ready_settings(market_data_provider="EODHD")
    assert build_market_data_provider(settings, http_fetcher=_noop_fetcher) is not None
