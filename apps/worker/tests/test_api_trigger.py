"""Tests for the worker → API HTTP triggers.

The helpers must:

* No-op (and not raise) when no base URL is configured.
* No-op (and not raise) on transport failure or non-2xx response — a
  scheduled tick must never crash the scheduler loop.
* Return the JSON body when the request lands cleanly.
"""

from __future__ import annotations

from typing import Any

from portfolio_outlook_worker import api_trigger


class _StubResponse:
    def __init__(self, *, status_code: int = 200, payload: Any | None = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {"status": "ok"}

    def json(self) -> Any:
        return self._payload


def test_trigger_morning_chain_noops_without_base_url() -> None:
    assert api_trigger.trigger_morning_chain(
        base_url=None, timeout_seconds=1.0
    ) is None


def test_trigger_morning_chain_returns_json_on_success(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_post(url: str, timeout: float) -> _StubResponse:
        captured["url"] = url
        captured["timeout"] = timeout
        return _StubResponse(payload={"status": "ok", "run_id": "sch_x"})

    # Stub the lazy httpx import inside the helper.
    import httpx

    monkeypatch.setattr(httpx, "post", _fake_post)

    body = api_trigger.trigger_morning_chain(
        base_url="http://api:8000", timeout_seconds=42.0
    )
    assert body == {"status": "ok", "run_id": "sch_x"}
    assert captured["url"] == "http://api:8000/scheduler/runs/morning-chain"
    assert captured["timeout"] == 42.0


def test_trigger_strips_trailing_slash_on_base_url(monkeypatch) -> None:
    captured: dict[str, str] = {}
    import httpx

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, timeout: (captured.__setitem__("url", url) or _StubResponse()),
    )
    api_trigger.trigger_morning_chain(base_url="http://api:8000/", timeout_seconds=1.0)
    # No double slash, even if the base URL was passed with one.
    assert captured["url"] == "http://api:8000/scheduler/runs/morning-chain"


def test_trigger_returns_none_on_transport_failure(monkeypatch) -> None:
    import httpx

    def _boom(url: str, timeout: float) -> _StubResponse:
        raise RuntimeError("connection refused")

    monkeypatch.setattr(httpx, "post", _boom)
    assert api_trigger.trigger_morning_chain(
        base_url="http://api:8000", timeout_seconds=1.0
    ) is None


def test_trigger_returns_none_on_http_error(monkeypatch) -> None:
    import httpx

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, timeout: _StubResponse(status_code=503, payload={"err": "down"}),
    )
    assert api_trigger.trigger_morning_chain(
        base_url="http://api:8000", timeout_seconds=1.0
    ) is None


def test_trigger_ibkr_sync_targets_correct_path(monkeypatch) -> None:
    captured: dict[str, str] = {}
    import httpx

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, timeout: (captured.__setitem__("url", url) or _StubResponse()),
    )
    api_trigger.trigger_ibkr_sync(base_url="http://api:8000", timeout_seconds=1.0)
    assert captured["url"] == "http://api:8000/ibkr/sync/run"


def test_trigger_morning_explanation_batch_targets_correct_path(monkeypatch) -> None:
    captured: dict[str, str] = {}
    import httpx

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, timeout: (captured.__setitem__("url", url) or _StubResponse()),
    )
    api_trigger.trigger_morning_explanation_batch(
        base_url="http://api:8000", timeout_seconds=1.0
    )
    assert captured["url"] == "http://api:8000/explanations/morning-batch"


def test_trigger_morning_explanation_batch_noops_without_base_url() -> None:
    assert api_trigger.trigger_morning_explanation_batch(
        base_url=None, timeout_seconds=1.0
    ) is None


def test_trigger_morning_explanation_batch_returns_none_on_http_error(
    monkeypatch,
) -> None:
    import httpx

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, timeout: _StubResponse(status_code=503, payload={"err": "down"}),
    )
    assert api_trigger.trigger_morning_explanation_batch(
        base_url="http://api:8000", timeout_seconds=1.0
    ) is None


def test_compose_alert_summary_posts_json_body_with_alerts(monkeypatch) -> None:
    captured: dict[str, object] = {}
    import httpx

    def _fake_post(url, timeout, json):
        captured["url"] = url
        captured["timeout"] = timeout
        captured["json"] = json
        return _StubResponse(
            payload={
                "status": "generated",
                "summary_nl": "Korte samenvatting.",
                "blocking_reason": None,
                "hallucinated_numbers": [],
                "safe_for_orders": False,
            }
        )

    monkeypatch.setattr(httpx, "post", _fake_post)

    body = api_trigger.compose_alert_summary(
        base_url="http://api:8000",
        timeout_seconds=2.5,
        kind="digest",
        context_text="Markt: EURONEXT.",
        alert_lines=["- [Hoog] X: Y"],
    )
    assert body == {
        "status": "generated",
        "summary_nl": "Korte samenvatting.",
        "blocking_reason": None,
        "hallucinated_numbers": [],
        "safe_for_orders": False,
    }
    assert captured["url"] == "http://api:8000/notifications/compose-summary"
    assert captured["timeout"] == 2.5
    assert captured["json"] == {
        "kind": "digest",
        "context_text": "Markt: EURONEXT.",
        "alert_lines": ["- [Hoog] X: Y"],
    }


def test_compose_alert_summary_returns_none_without_base_url() -> None:
    assert api_trigger.compose_alert_summary(
        base_url=None,
        timeout_seconds=1.0,
        kind="digest",
        context_text="",
        alert_lines=[],
    ) is None


def test_compose_alert_summary_returns_none_on_http_error(monkeypatch) -> None:
    import httpx

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, timeout, json: _StubResponse(status_code=503, payload={}),
    )
    assert api_trigger.compose_alert_summary(
        base_url="http://api:8000",
        timeout_seconds=1.0,
        kind="digest",
        context_text="",
        alert_lines=["- [Hoog] X: Y"],
    ) is None
