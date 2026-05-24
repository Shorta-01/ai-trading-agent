"""Minimal EODHD HTTP client for real-time quotes and FX rates.

Uses stdlib ``urllib`` so the API has zero extra dependencies. The HTTP backend
is injectable so tests run without network. The client only does GET requests
against documented EODHD endpoints:

* Quotes:  ``GET {base_url}/real-time/{SYMBOL}.{EX}?api_token={key}&fmt=json``
* FX:      ``GET {base_url}/real-time/{BASE}{QUOTE}.FOREX?api_token={key}&fmt=json``

EODHD's real-time JSON payload has shape::

    {
      "code": "AAPL.US",
      "timestamp": 1715000000,
      "gmtoffset": 0,
      "open": 180.10, "high": 182.20, "low": 179.50,
      "close": 181.40, "volume": 47000000,
      "previousClose": 180.00, "change": 1.40, "change_p": 0.78
    }

We treat ``close`` as the latest known price (EODHD docs explicitly call it
"current price" during market hours and the last close after). ``previousClose``
is used to compute ``day_change_percent`` only when EODHD omits ``change_p``.

This module is HTTP-only — it does not touch storage, settings, or the
``MarketDataLatestSnapshotRecord`` shape. Mapping to storage records lives in
``market_data_sync``.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

logger = logging.getLogger(__name__)

HttpFetcher = Callable[[str, int], "EodhdHttpResponse"]


@dataclass(frozen=True)
class EodhdHttpResponse:
    """Raw HTTP response captured for the parser layer."""

    status_code: int
    body: str


@dataclass(frozen=True)
class EodhdQuote:
    """Parsed EODHD real-time quote.

    Field names match the EODHD JSON keys 1:1 so the parser is auditable.
    """

    code: str
    last_price: Decimal | None
    open_price: Decimal | None
    high_price: Decimal | None
    low_price: Decimal | None
    previous_close: Decimal | None
    day_change_percent: Decimal | None
    volume: Decimal | None
    provider_as_of: datetime | None


@dataclass(frozen=True)
class EodhdFxRate:
    """Parsed EODHD FX rate. EODHD encodes the pair as ``{BASE}{QUOTE}.FOREX``,
    so the returned rate is "1 BASE = X QUOTE"."""

    pair_code: str
    base_currency: str
    quote_currency: str
    rate: Decimal | None
    previous_close: Decimal | None
    provider_as_of: datetime | None


@dataclass(frozen=True)
class EodhdBar:
    """Parsed EODHD historical daily bar from ``/eod/{symbol}``."""

    bar_date: date
    open_price: Decimal | None
    high_price: Decimal | None
    low_price: Decimal | None
    close_price: Decimal | None
    adjusted_close: Decimal | None
    volume: Decimal | None


class EodhdClientError(Exception):
    """Raised when the HTTP layer or response parsing fails."""


class EodhdAuthError(EodhdClientError):
    """Raised when EODHD returns 401/403 (bad/missing API key)."""


class EodhdNotFoundError(EodhdClientError):
    """Raised when the requested symbol or pair is unknown to EODHD."""


class EodhdRateLimitError(EodhdClientError):
    """Raised when EODHD returns 429 (rate limited)."""


class _DefaultHttpFetcher:
    """Stdlib-based HTTP fetcher with a strict timeout."""

    def __call__(self, url: str, timeout_seconds: int) -> EodhdHttpResponse:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body_bytes = response.read()
                status_code = int(getattr(response, "status", 200))
        except urllib.error.HTTPError as exc:
            body_bytes = exc.read() if exc.fp is not None else b""
            status_code = int(exc.code)
        except (urllib.error.URLError, TimeoutError) as exc:
            raise EodhdClientError(f"network_error: {exc}") from exc
        try:
            body_text = body_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EodhdClientError(f"decode_error: {exc}") from exc
        return EodhdHttpResponse(status_code=status_code, body=body_text)


class EodhdClient:
    """Read-only EODHD client for real-time quotes and FX rates."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://eodhd.com/api",
        request_timeout_seconds: int = 10,
        http_fetcher: HttpFetcher | None = None,
    ) -> None:
        if not api_key:
            raise EodhdAuthError("missing_api_key")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = max(1, int(request_timeout_seconds))
        self._fetch: HttpFetcher = http_fetcher or _DefaultHttpFetcher()

    def fetch_quote(self, eodhd_symbol: str) -> EodhdQuote:
        """Fetch a real-time / latest-close quote for one EODHD symbol such as
        ``AAPL.US`` or ``ASML.AS``."""

        cleaned = eodhd_symbol.strip()
        if not cleaned:
            raise EodhdClientError("empty_symbol")
        url = self._build_url(f"real-time/{urllib.parse.quote(cleaned, safe='.')}")
        payload = self._get(url)
        return _parse_quote(cleaned, payload)

    def fetch_fx_rate(self, base_currency: str, quote_currency: str) -> EodhdFxRate:
        """Fetch a real-time FX rate. ``base_currency``/``quote_currency`` use
        ISO-4217 three-letter codes (USD, EUR, GBP, ...).

        EODHD's FX symbol format is ``{BASE}{QUOTE}.FOREX``.
        """

        base = base_currency.strip().upper()
        quote = quote_currency.strip().upper()
        if len(base) != 3 or len(quote) != 3 or not base.isalpha() or not quote.isalpha():
            raise EodhdClientError(f"invalid_currency_pair:{base}{quote}")
        pair_code = f"{base}{quote}.FOREX"
        url = self._build_url(f"real-time/{pair_code}")
        payload = self._get(url)
        return _parse_fx_rate(pair_code, base, quote, payload)

    def fetch_eod_bars(
        self,
        eodhd_symbol: str,
        *,
        from_date: date,
        to_date: date,
    ) -> list[EodhdBar]:
        """Fetch historical daily bars for one EODHD symbol.

        Endpoint: ``/eod/{SYMBOL.EX}?from=YYYY-MM-DD&to=YYYY-MM-DD&period=d``.
        Returns chronologically sorted bars; gaps (holidays, halts) are
        naturally absent.
        """

        cleaned = eodhd_symbol.strip()
        if not cleaned:
            raise EodhdClientError("empty_symbol")
        if from_date > to_date:
            raise EodhdClientError("from_date_after_to_date")
        path = f"eod/{urllib.parse.quote(cleaned, safe='.')}"
        extra = {"from": from_date.isoformat(), "to": to_date.isoformat(), "period": "d"}
        url = self._build_url(path, extra=extra)
        payload = self._get(url)
        return _parse_eod_bars(payload)

    # ---- private helpers ----

    def _build_url(self, path: str, *, extra: dict[str, str] | None = None) -> str:
        params: dict[str, str] = {"api_token": self._api_key, "fmt": "json"}
        if extra is not None:
            params.update(extra)
        query = urllib.parse.urlencode(params)
        return f"{self._base_url}/{path.lstrip('/')}?{query}"

    def _get(self, url: str) -> object:
        response = self._fetch(url, self._timeout)
        if response.status_code in (401, 403):
            raise EodhdAuthError(f"auth_error: status={response.status_code}")
        if response.status_code == 404:
            raise EodhdNotFoundError(f"not_found: status={response.status_code}")
        if response.status_code == 429:
            raise EodhdRateLimitError("rate_limited")
        if response.status_code >= 500:
            raise EodhdClientError(f"server_error: status={response.status_code}")
        if response.status_code >= 400:
            raise EodhdClientError(f"http_error: status={response.status_code}")
        try:
            return json.loads(response.body)
        except json.JSONDecodeError as exc:
            raise EodhdClientError(f"invalid_json: {exc}") from exc


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text.upper() in {"NA", "N/A", "NULL", "NONE"}:
            return None
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return None
    return None


def _timestamp_or_none(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, int | float) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(int(value), tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromtimestamp(int(text), tz=UTC)
        except (ValueError, OverflowError, OSError):
            pass
        try:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except ValueError:
            return None
    return None


def _parse_quote(eodhd_symbol: str, payload: object) -> EodhdQuote:
    if not isinstance(payload, dict):
        raise EodhdClientError("quote_payload_not_object")
    raw_code = str(payload.get("code") or eodhd_symbol)
    last = _decimal_or_none(payload.get("close"))
    open_price = _decimal_or_none(payload.get("open"))
    high = _decimal_or_none(payload.get("high"))
    low = _decimal_or_none(payload.get("low"))
    previous_close = _decimal_or_none(payload.get("previousClose"))
    change_pct = _decimal_or_none(payload.get("change_p"))
    if (
        change_pct is None
        and last is not None
        and previous_close is not None
        and previous_close != 0
    ):
        try:
            change_pct = ((last - previous_close) / previous_close) * Decimal("100")
        except (InvalidOperation, ZeroDivisionError):
            change_pct = None
    return EodhdQuote(
        code=raw_code,
        last_price=last,
        open_price=open_price,
        high_price=high,
        low_price=low,
        previous_close=previous_close,
        day_change_percent=change_pct,
        volume=_decimal_or_none(payload.get("volume")),
        provider_as_of=_timestamp_or_none(payload.get("timestamp")),
    )


def _parse_fx_rate(
    pair_code: str,
    base_currency: str,
    quote_currency: str,
    payload: object,
) -> EodhdFxRate:
    if not isinstance(payload, dict):
        raise EodhdClientError("fx_payload_not_object")
    return EodhdFxRate(
        pair_code=str(payload.get("code") or pair_code),
        base_currency=base_currency,
        quote_currency=quote_currency,
        rate=_decimal_or_none(payload.get("close")),
        previous_close=_decimal_or_none(payload.get("previousClose")),
        provider_as_of=_timestamp_or_none(payload.get("timestamp")),
    )


def _parse_eod_bars(payload: object) -> list[EodhdBar]:
    if not isinstance(payload, list):
        raise EodhdClientError("eod_payload_not_array")
    bars: list[EodhdBar] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        date_str = str(item.get("date") or "").strip()
        if not date_str:
            continue
        try:
            bar_date = date.fromisoformat(date_str)
        except ValueError:
            continue
        bars.append(
            EodhdBar(
                bar_date=bar_date,
                open_price=_decimal_or_none(item.get("open")),
                high_price=_decimal_or_none(item.get("high")),
                low_price=_decimal_or_none(item.get("low")),
                close_price=_decimal_or_none(item.get("close")),
                adjusted_close=_decimal_or_none(item.get("adjusted_close")),
                volume=_decimal_or_none(item.get("volume")),
            )
        )
    bars.sort(key=lambda b: b.bar_date)
    return bars


class EodhdMarketDataProvider(Protocol):
    """Narrow protocol so ``market_data_sync`` can inject a fake in tests."""

    def fetch_quote(self, eodhd_symbol: str) -> EodhdQuote: ...

    def fetch_fx_rate(self, base_currency: str, quote_currency: str) -> EodhdFxRate: ...


class EodhdHistoricalProvider(Protocol):
    """Narrow protocol for fetching historical bars (used by forecast sync)."""

    def fetch_eod_bars(
        self,
        eodhd_symbol: str,
        *,
        from_date: date,
        to_date: date,
    ) -> list[EodhdBar]: ...
