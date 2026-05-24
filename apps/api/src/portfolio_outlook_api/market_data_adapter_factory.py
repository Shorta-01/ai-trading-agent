"""Factory that picks the configured market-data provider, or ``None``.

Mirrors the design of ``ibkr_sync_adapter_factory``: a single gate point
returns either a real provider (currently EODHD) or ``None``. ``None`` means
the route handler must report "not configured" rather than fall back to fake
data.
"""

from __future__ import annotations

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.eodhd_client import (
    EodhdAuthError,
    EodhdClient,
    HttpFetcher,
)


def build_market_data_provider(
    settings: Settings,
    *,
    http_fetcher: HttpFetcher | None = None,
) -> EodhdClient | None:
    """Return a real EODHD client when fully configured, else ``None``.

    Gates:

    * ``settings.market_data_sync_enabled`` must be True.
    * ``settings.market_data_provider`` must be ``"eodhd"`` (other providers
      may follow in a later slice).
    * ``settings.eodhd_enabled`` must be True.
    * ``settings.eodhd_api_key`` must be present.

    The factory accepts an optional ``http_fetcher`` so tests can drive the
    real ``EodhdClient`` against a fake HTTP backend.
    """

    if not settings.market_data_sync_enabled:
        return None
    if settings.market_data_provider.lower() != "eodhd":
        return None
    if not settings.eodhd_enabled:
        return None
    api_key = settings.eodhd_api_key
    if not api_key:
        return None
    try:
        return EodhdClient(
            api_key=api_key,
            base_url=settings.eodhd_base_url,
            request_timeout_seconds=settings.eodhd_request_timeout_seconds,
            http_fetcher=http_fetcher,
        )
    except EodhdAuthError:
        return None
