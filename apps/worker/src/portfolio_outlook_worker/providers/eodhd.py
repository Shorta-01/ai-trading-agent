"""Task 129: EODHD provider client.

Lives in the worker process — the API never touches EODHD directly.

* ``fetch_eod(symbol, exchange, as_of_date)`` — `GET /api/eod/{symbol}.{exchange}`.
* ``fetch_fx(base, quote, as_of_date)`` — `GET /api/eod/{base}{quote}.FOREX`.

Both methods:

* Coerce every numeric to ``Decimal`` via the string form (never float).
* Retry once on 5xx with 2s backoff. No retry on 4xx.
* Honour the configurable per-second rate limit (default 10 r/s,
  well below the 20 r/s EODHD ceiling).
* Write one ``ProviderCallAuditEntry`` row per call (success or
  failure).
* Return :class:`EodhdNotConfiguredError` when ``api_key=None``
  without touching the network.

The HTTP client is injectable so tests can supply a fake without
adding ``httpx`` as a hard test-time dep.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    EodhdNotConfiguredError,
    ProviderCallAuditEntry,
    SqlAlchemyProviderCallAuditRepository,
)

logger = logging.getLogger(__name__)


PROVIDER_CODE = "eodhd"
_DEFAULT_TIMEOUT_SECONDS = 8.0
_RETRY_BACKOFF_SECONDS = 2.0


class _HttpClientProtocol(Protocol):
    """Minimal HTTP surface the EODHD client uses.

    Defined as a Protocol so tests can inject a fake without
    importing ``httpx`` at module load time.
    """

    def get(
        self, url: str, *, params: dict[str, Any], timeout: float
    ) -> Any: ...


@dataclass(frozen=True)
class EodResponse:
    """Parsed EODHD EOD response."""

    symbol: str
    exchange: str
    as_of_date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal
    adjusted_close: Decimal | None
    volume: int | None
    raw_hash: str


@dataclass(frozen=True)
class FxResponse:
    """Parsed EODHD FX response."""

    base: str
    quote: str
    as_of_date: date
    rate: Decimal
    raw_hash: str


class _RateLimiter:
    """Simple token-bucket-style limiter.

    Threading-safe; refills one token every ``1/rate_per_second``
    seconds. Calling ``acquire()`` blocks until a token is
    available. Synchronous to match the worker's threading model
    (APScheduler's BackgroundScheduler).
    """

    def __init__(self, *, rate_per_second: int) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        self._interval = 1.0 / float(rate_per_second)
        self._next_allowed_at = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed_at:
                time.sleep(self._next_allowed_at - now)
                now = time.monotonic()
            self._next_allowed_at = max(now, self._next_allowed_at) + self._interval


class EodhdClient:
    """Production EODHD client wired to ``ProviderCallAuditRepository``."""

    def __init__(
        self,
        *,
        api_key: str | None,
        audit_repo: SqlAlchemyProviderCallAuditRepository | None = None,
        http_client: _HttpClientProtocol | None = None,
        base_url: str = "https://eodhd.com/api",
        rate_limit_per_second: int = 10,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        account_id: str | None = None,
        triggered_by_run_id: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._audit_repo = audit_repo
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._rate_limiter = _RateLimiter(
            rate_per_second=rate_limit_per_second
        )
        self._clock = clock
        self._sleep = sleep
        self._account_id = account_id
        self._triggered_by_run_id = triggered_by_run_id

    def fetch_eod(
        self,
        *,
        symbol: str,
        exchange: str,
        as_of_date: date,
    ) -> EodResponse:
        if self._api_key is None:
            raise EodhdNotConfiguredError(
                "EODHD_API_KEY is not configured; skipping fetch."
            )
        endpoint = f"/eod/{symbol}.{exchange}"
        params = {
            "api_token": self._api_key,
            "fmt": "json",
            "from": as_of_date.isoformat(),
            "to": as_of_date.isoformat(),
        }
        body = self._request(endpoint=endpoint, params=params)
        return _parse_eod_response(
            symbol=symbol,
            exchange=exchange,
            as_of_date=as_of_date,
            body=body,
        )

    def fetch_fx(
        self,
        *,
        base: str,
        quote: str,
        as_of_date: date,
    ) -> FxResponse:
        if self._api_key is None:
            raise EodhdNotConfiguredError(
                "EODHD_API_KEY is not configured; skipping fetch."
            )
        endpoint = f"/eod/{base}{quote}.FOREX"
        params = {
            "api_token": self._api_key,
            "fmt": "json",
            "from": as_of_date.isoformat(),
            "to": as_of_date.isoformat(),
        }
        body = self._request(endpoint=endpoint, params=params)
        return _parse_fx_response(
            base=base, quote=quote, as_of_date=as_of_date, body=body
        )

    # ---- internals -----------------------------------------------

    def _request(
        self,
        *,
        endpoint: str,
        params: dict[str, Any],
    ) -> Any:
        if self._http_client is None:
            self._http_client = _default_http_client_factory()

        url = f"{self._base_url}{endpoint}"
        last_exc: Exception | None = None
        last_status: int | None = None
        for attempt in (1, 2):
            self._rate_limiter.acquire()
            started = time.monotonic()
            try:
                response = self._http_client.get(
                    url, params=params, timeout=_DEFAULT_TIMEOUT_SECONDS
                )
                status_code = int(getattr(response, "status_code", 0))
                last_status = status_code
                body_text = _safe_text(response)
                if 200 <= status_code < 300:
                    self._log_call(
                        endpoint=endpoint,
                        params=params,
                        status=status_code,
                        size=len(body_text or ""),
                        duration_ms=_elapsed_ms(started),
                        error_class=None,
                        error_details=None,
                    )
                    return json.loads(body_text)
                # 5xx → retry once
                if 500 <= status_code < 600 and attempt == 1:
                    self._log_call(
                        endpoint=endpoint,
                        params=params,
                        status=status_code,
                        size=len(body_text or ""),
                        duration_ms=_elapsed_ms(started),
                        error_class="HTTPStatusError",
                        error_details={"retry": True, "status": status_code},
                    )
                    self._sleep(_RETRY_BACKOFF_SECONDS)
                    continue
                # 4xx or 5xx on second attempt → give up
                self._log_call(
                    endpoint=endpoint,
                    params=params,
                    status=status_code,
                    size=len(body_text or ""),
                    duration_ms=_elapsed_ms(started),
                    error_class="HTTPStatusError",
                    error_details={"status": status_code, "body": body_text[:512]},
                )
                raise RuntimeError(
                    f"EODHD request failed: HTTP {status_code}"
                )
            except Exception as exc:  # noqa: BLE001 — boundary
                last_exc = exc
                if isinstance(exc, RuntimeError) and "EODHD request failed" in str(exc):
                    raise
                self._log_call(
                    endpoint=endpoint,
                    params=params,
                    status=last_status,
                    size=None,
                    duration_ms=_elapsed_ms(started),
                    error_class=type(exc).__name__,
                    error_details={"message": str(exc)},
                )
                if attempt == 1:
                    self._sleep(_RETRY_BACKOFF_SECONDS)
                    continue
                raise
        # Defensive: loop ended without return → propagate the last error.
        raise RuntimeError(
            f"EODHD request failed after retry: {last_exc!r}"
        )

    def _log_call(
        self,
        *,
        endpoint: str,
        params: dict[str, Any],
        status: int | None,
        size: int | None,
        duration_ms: int,
        error_class: str | None,
        error_details: dict[str, Any] | None,
    ) -> None:
        if self._audit_repo is None:
            return
        # Strip the api_token before persisting — never leak credentials.
        sanitised = {k: v for k, v in params.items() if k != "api_token"}
        try:
            self._audit_repo.append(
                ProviderCallAuditEntry(
                    audit_id=f"pcaud_{uuid4().hex}",
                    called_at=self._clock(),
                    provider=PROVIDER_CODE,
                    endpoint=endpoint,
                    request_params_json=json.dumps(sanitised),
                    response_status=status,
                    response_size_bytes=size,
                    duration_ms=duration_ms,
                    error_class=error_class,
                    error_details_json=(
                        None if error_details is None else json.dumps(error_details)
                    ),
                    account_id=self._account_id,
                    triggered_by_run_id=self._triggered_by_run_id,
                )
            )
        except Exception:  # noqa: BLE001 — boundary
            logger.exception("Failed to persist provider-call audit row")


# ---- parsers + helpers -------------------------------------------


def _parse_eod_response(
    *,
    symbol: str,
    exchange: str,
    as_of_date: date,
    body: Any,
) -> EodResponse:
    if not isinstance(body, list) or not body:
        raise RuntimeError("EODHD EOD response is empty")
    row = body[0]
    if not isinstance(row, dict):
        raise RuntimeError("EODHD EOD response row malformed")
    close_raw = row.get("close")
    if close_raw is None:
        raise RuntimeError("EODHD EOD response missing close")
    raw_hash = hashlib.sha256(
        json.dumps(row, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return EodResponse(
        symbol=symbol,
        exchange=exchange,
        as_of_date=as_of_date,
        open=_decimal_or_none(row.get("open")),
        high=_decimal_or_none(row.get("high")),
        low=_decimal_or_none(row.get("low")),
        close=_decimal_required(close_raw),
        adjusted_close=_decimal_or_none(row.get("adjusted_close")),
        volume=_int_or_none(row.get("volume")),
        raw_hash=raw_hash,
    )


def _parse_fx_response(
    *,
    base: str,
    quote: str,
    as_of_date: date,
    body: Any,
) -> FxResponse:
    if not isinstance(body, list) or not body:
        raise RuntimeError("EODHD FX response is empty")
    row = body[0]
    if not isinstance(row, dict):
        raise RuntimeError("EODHD FX response row malformed")
    close_raw = row.get("close") or row.get("adjusted_close")
    if close_raw is None:
        raise RuntimeError("EODHD FX response missing close")
    raw_hash = hashlib.sha256(
        json.dumps(row, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return FxResponse(
        base=base,
        quote=quote,
        as_of_date=as_of_date,
        rate=_decimal_required(close_raw),
        raw_hash=raw_hash,
    )


def _decimal_required(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return _decimal_required(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text is not None:
        return str(text)
    return ""


def _elapsed_ms(started_monotonic: float) -> int:
    return max(0, int((time.monotonic() - started_monotonic) * 1000))


def _default_http_client_factory() -> _HttpClientProtocol:
    """Production HTTP client. Lazily import ``httpx`` so the
    module stays loadable without the dep installed (tests inject
    a fake)."""

    import httpx

    client: _HttpClientProtocol = httpx.Client()
    return client
