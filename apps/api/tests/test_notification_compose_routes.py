"""Endpoint tests for ``POST /notifications/compose-summary``.

Worker-only consumer. The endpoint:

* Returns ``status="disabled"`` when ``ai_email_summary_enabled`` is off.
* Returns HTTP 400 when ``kind`` is unrecognised — clamps to digest /
  morning_alerts so a typo can't slip into the prompt.
* Happy path: stub provider produces a Dutch summary that ends with
  the locked risk disclaimer; the endpoint passes it through.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from portfolio_outlook_portfolio import LOCKED_RISK_DISCLAIMER_NL

from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.ai_explanation_enabled = False
    api_settings.ai_explanation_real_client_enabled = False
    api_settings.ai_explanation_provider_code = "stub"
    api_settings.ai_explanation_max_output_chars = 2000
    api_settings.ai_email_summary_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_returns_disabled_when_flag_off() -> None:
    r = client.post(
        "/notifications/compose-summary",
        json={
            "kind": "digest",
            "context_text": "X",
            "alert_lines": ["- [Hoog] X: Y"],
        },
    )
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "disabled"
    assert body["summary_nl"] is None
    assert body["safe_for_orders"] is False


def test_returns_400_on_unknown_kind() -> None:
    api_settings.ai_email_summary_enabled = True
    api_settings.ai_explanation_enabled = True
    r = client.post(
        "/notifications/compose-summary",
        json={"kind": "weekly", "context_text": "X", "alert_lines": []},
    )
    assert r.status_code == 400


def test_happy_path_with_stub_provider() -> None:
    api_settings.ai_email_summary_enabled = True
    api_settings.ai_explanation_enabled = True
    api_settings.ai_explanation_provider_code = "stub"

    r = client.post(
        "/notifications/compose-summary",
        json={
            "kind": "digest",
            "context_text": (
                "Markt: EURONEXT. Datum: 2026-05-31. NAV: 0.50% (EUR)."
            ),
            "alert_lines": [
                "- [Hoog] NAV-daling: Portfolio NAV daalde met 2.5%.",
            ],
        },
    )
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "generated"
    assert body["summary_nl"] is not None
    assert LOCKED_RISK_DISCLAIMER_NL in body["summary_nl"]
    assert body["hallucinated_numbers"] == []
    assert body["safe_for_orders"] is False


def test_provider_unavailable_with_no_ai_explanation_enabled() -> None:
    # Master compose flag is on, but the explanation provider is
    # disabled (gating on ``ai_explanation_enabled``). The endpoint
    # should surface ``provider_unavailable`` so the worker falls
    # through to template-only — not crash.
    api_settings.ai_email_summary_enabled = True
    api_settings.ai_explanation_enabled = False

    r = client.post(
        "/notifications/compose-summary",
        json={
            "kind": "morning_alerts",
            "context_text": "Ochtend-alerts voor 2026-06-01.",
            "alert_lines": ["- [Hoog] Verkoop AAPL: Hoge zekerheid."],
        },
    )
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "provider_unavailable"
    assert body["summary_nl"] is None
    assert body["blocking_reason"] == "ai_explanation_disabled"


def test_empty_alerts_skips_silently() -> None:
    api_settings.ai_email_summary_enabled = True
    api_settings.ai_explanation_enabled = True
    api_settings.ai_explanation_provider_code = "stub"

    r = client.post(
        "/notifications/compose-summary",
        json={"kind": "digest", "context_text": "X", "alert_lines": []},
    )
    body = r.json()
    assert body["status"] == "skipped_no_alerts"
    assert body["summary_nl"] is None
