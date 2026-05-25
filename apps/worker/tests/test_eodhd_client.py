"""Task 129 — EodhdClient tests with injected HTTP fakes."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from ai_trading_agent_storage import (
    EodhdNotConfiguredError,
    ProviderCallAuditEntry,
)

from portfolio_outlook_worker.providers.eodhd import EodhdClient

_BASE_DATE = date(2026, 5, 24)


class _FakeResponse:
    def __init__(self, *, status_code: int, body: object) -> None:
        self.status_code = status_code
        if isinstance(body, str):
            self.text = body
        else:
            self.text = json.dumps(body)


class _FakeHttpClient:
    """Records every call + returns canned responses in order."""

    def __init__(
        self,
        *,
        responses: list[_FakeResponse | Exception],
    ) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(
        self, url: str, *, params: dict[str, Any], timeout: float
    ) -> _FakeResponse:
        self.calls.append({"url": url, "params": dict(params), "timeout": timeout})
        nxt = self._responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


class _RecordingAuditRepo:
    def __init__(self) -> None:
        self.records: list[ProviderCallAuditEntry] = []

    def append(self, record: ProviderCallAuditEntry) -> object:
        self.records.append(record)
        return record


_HAPPY_BODY = [
    {
        "date": "2026-05-24",
        "open": "635.0",
        "high": "642.5",
        "low": "634.0",
        "close": "640.123456",
        "adjusted_close": "640.123456",
        "volume": "123456",
    }
]


# ---- not configured ----------------------------------------------


def test_fetch_eod_raises_not_configured_without_api_key() -> None:
    client = EodhdClient(api_key=None)
    with pytest.raises(EodhdNotConfiguredError):
        client.fetch_eod(symbol="ASML", exchange="AEB", as_of_date=_BASE_DATE)


def test_fetch_fx_raises_not_configured_without_api_key() -> None:
    client = EodhdClient(api_key=None)
    with pytest.raises(EodhdNotConfiguredError):
        client.fetch_fx(base="USD", quote="EUR", as_of_date=_BASE_DATE)


# ---- happy path Decimal precision --------------------------------


def test_fetch_eod_parses_decimal_preserving_precision() -> None:
    http = _FakeHttpClient(responses=[_FakeResponse(status_code=200, body=_HAPPY_BODY)])
    audit = _RecordingAuditRepo()
    client = EodhdClient(
        api_key="testkey",
        audit_repo=audit,  # type: ignore[arg-type]
        http_client=http,
        sleep=lambda _s: None,
    )
    response = client.fetch_eod(
        symbol="ASML", exchange="AEB", as_of_date=_BASE_DATE
    )
    assert response.symbol == "ASML"
    assert response.exchange == "AEB"
    assert response.close == Decimal("640.123456")
    assert response.open == Decimal("635.0")
    assert response.high == Decimal("642.5")
    assert response.low == Decimal("634.0")
    assert response.adjusted_close == Decimal("640.123456")
    assert response.volume == 123456
    assert response.raw_hash  # non-empty hash

    # Exactly one audit row for the call; api_token stripped.
    assert len(audit.records) == 1
    persisted_params = json.loads(audit.records[0].request_params_json or "{}")
    assert "api_token" not in persisted_params
    assert audit.records[0].response_status == 200
    assert audit.records[0].error_class is None


def test_fetch_fx_parses_rate_as_decimal() -> None:
    fx_body = [{"date": "2026-05-24", "close": "1.182345", "adjusted_close": "1.182345"}]
    http = _FakeHttpClient(responses=[_FakeResponse(status_code=200, body=fx_body)])
    client = EodhdClient(
        api_key="testkey", http_client=http, sleep=lambda _s: None
    )
    response = client.fetch_fx(base="GBP", quote="EUR", as_of_date=_BASE_DATE)
    assert response.base == "GBP"
    assert response.quote == "EUR"
    assert response.rate == Decimal("1.182345")


# ---- retry semantics ---------------------------------------------


def test_fetch_eod_retries_once_on_5xx_then_succeeds() -> None:
    http = _FakeHttpClient(
        responses=[
            _FakeResponse(status_code=503, body=""),
            _FakeResponse(status_code=200, body=_HAPPY_BODY),
        ]
    )
    audit = _RecordingAuditRepo()
    client = EodhdClient(
        api_key="testkey",
        audit_repo=audit,  # type: ignore[arg-type]
        http_client=http,
        sleep=lambda _s: None,
    )
    response = client.fetch_eod(
        symbol="ASML", exchange="AEB", as_of_date=_BASE_DATE
    )
    assert response.close == Decimal("640.123456")
    # Two HTTP calls + two audit rows (the 5xx attempt is logged too).
    assert len(http.calls) == 2
    assert len(audit.records) == 2
    assert audit.records[0].response_status == 503
    assert audit.records[1].response_status == 200


def test_fetch_eod_gives_up_after_two_5xx_attempts() -> None:
    http = _FakeHttpClient(
        responses=[
            _FakeResponse(status_code=503, body=""),
            _FakeResponse(status_code=503, body=""),
        ]
    )
    audit = _RecordingAuditRepo()
    client = EodhdClient(
        api_key="testkey",
        audit_repo=audit,  # type: ignore[arg-type]
        http_client=http,
        sleep=lambda _s: None,
    )
    with pytest.raises(RuntimeError, match="HTTP 503"):
        client.fetch_eod(
            symbol="ASML", exchange="AEB", as_of_date=_BASE_DATE
        )
    assert len(http.calls) == 2
    # Two audit rows for the two attempts.
    assert len(audit.records) == 2


def test_fetch_eod_does_not_retry_on_4xx() -> None:
    http = _FakeHttpClient(
        responses=[_FakeResponse(status_code=404, body="Not found")]
    )
    audit = _RecordingAuditRepo()
    client = EodhdClient(
        api_key="testkey",
        audit_repo=audit,  # type: ignore[arg-type]
        http_client=http,
        sleep=lambda _s: None,
    )
    with pytest.raises(RuntimeError, match="HTTP 404"):
        client.fetch_eod(
            symbol="ASML", exchange="AEB", as_of_date=_BASE_DATE
        )
    assert len(http.calls) == 1  # no retry
    assert len(audit.records) == 1
    assert audit.records[0].response_status == 404


def test_fetch_eod_logs_call_even_when_http_raises() -> None:
    http = _FakeHttpClient(responses=[ConnectionError("network down")])
    audit = _RecordingAuditRepo()
    client = EodhdClient(
        api_key="testkey",
        audit_repo=audit,  # type: ignore[arg-type]
        http_client=http,
        sleep=lambda _s: None,
    )
    # Provide a second response so the retry can succeed.
    http._responses.append(_FakeResponse(status_code=200, body=_HAPPY_BODY))
    response = client.fetch_eod(
        symbol="ASML", exchange="AEB", as_of_date=_BASE_DATE
    )
    assert response.close == Decimal("640.123456")
    assert len(audit.records) == 2
    assert audit.records[0].error_class == "ConnectionError"


# ---- audit metadata ---------------------------------------------


def test_audit_row_carries_account_and_run_id() -> None:
    http = _FakeHttpClient(responses=[_FakeResponse(status_code=200, body=_HAPPY_BODY)])
    audit = _RecordingAuditRepo()
    client = EodhdClient(
        api_key="testkey",
        audit_repo=audit,  # type: ignore[arg-type]
        http_client=http,
        sleep=lambda _s: None,
        account_id="DU1234567",
        triggered_by_run_id="srun-abcdef",
    )
    client.fetch_eod(symbol="ASML", exchange="AEB", as_of_date=_BASE_DATE)
    assert audit.records[0].account_id == "DU1234567"
    assert audit.records[0].triggered_by_run_id == "srun-abcdef"


def test_audit_row_uses_clock_for_called_at() -> None:
    http = _FakeHttpClient(responses=[_FakeResponse(status_code=200, body=_HAPPY_BODY)])
    audit = _RecordingAuditRepo()
    fixed = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)
    client = EodhdClient(
        api_key="testkey",
        audit_repo=audit,  # type: ignore[arg-type]
        http_client=http,
        sleep=lambda _s: None,
        clock=lambda: fixed,
    )
    client.fetch_eod(symbol="ASML", exchange="AEB", as_of_date=_BASE_DATE)
    assert audit.records[0].called_at == fixed
