"""Tests voor /runbook endpoint (V1.2 §BH)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app


@pytest.fixture(autouse=True)
def _reset_settings():  # type: ignore[no-untyped-def]
    """Snapshot + restore alle relevante settings die runbook leest.

    Het hele test-bestand muteert flags rechtstreeks op de
    settings-singleton; zonder restore lekken de mutaties naar
    volgende tests.
    """

    snapshot = {
        "paper_only_mode": api_settings.paper_only_mode,
        "storage_enabled": api_settings.storage.enabled,
        "storage_database_url": api_settings.storage.database_url,
        "storage_writes_enabled": api_settings.storage.writes_enabled,
        "eodhd_api_key": api_settings.eodhd_api_key,
        "ibkr_enabled": api_settings.ibkr_enabled,
        "claude_ai_api_key": getattr(api_settings, "claude_ai_api_key", None),
        "market_data_sync_enabled": api_settings.market_data_sync_enabled,
        "forecast_sync_enabled": api_settings.forecast_sync_enabled,
        "suggestions_sync_enabled": api_settings.suggestions_sync_enabled,
        "decision_packages_sync_enabled": (
            api_settings.decision_packages_sync_enabled
        ),
        "action_drafts_sync_enabled": api_settings.action_drafts_sync_enabled,
        "earnings_calendar_sync_enabled": api_settings.earnings_calendar_sync_enabled,
        "orchestrator_scoring_enabled": api_settings.orchestrator_scoring_enabled,
        "daily_briefing_sync_enabled": api_settings.daily_briefing_sync_enabled,
    }
    yield
    api_settings.paper_only_mode = snapshot["paper_only_mode"]
    api_settings.storage.enabled = snapshot["storage_enabled"]
    api_settings.storage.database_url = snapshot["storage_database_url"]
    api_settings.storage.writes_enabled = snapshot["storage_writes_enabled"]
    api_settings.eodhd_api_key = snapshot["eodhd_api_key"]
    api_settings.ibkr_enabled = snapshot["ibkr_enabled"]
    api_settings.claude_ai_api_key = snapshot["claude_ai_api_key"]
    api_settings.market_data_sync_enabled = snapshot["market_data_sync_enabled"]
    api_settings.forecast_sync_enabled = snapshot["forecast_sync_enabled"]
    api_settings.suggestions_sync_enabled = snapshot["suggestions_sync_enabled"]
    api_settings.decision_packages_sync_enabled = snapshot[
        "decision_packages_sync_enabled"
    ]
    api_settings.action_drafts_sync_enabled = snapshot["action_drafts_sync_enabled"]
    api_settings.earnings_calendar_sync_enabled = snapshot[
        "earnings_calendar_sync_enabled"
    ]
    api_settings.orchestrator_scoring_enabled = snapshot["orchestrator_scoring_enabled"]
    api_settings.daily_briefing_sync_enabled = snapshot["daily_briefing_sync_enabled"]


def _client() -> TestClient:
    return TestClient(app)


def _items_by_code(body) -> dict:  # type: ignore[no-untyped-def]
    return {item["code"]: item for item in body["items"]}


# ----------------------------------------------------------------------
# Default state — fresh install with storage off
# ----------------------------------------------------------------------


def test_runbook_returns_structured_response() -> None:
    body = _client().get("/runbook").json()
    assert body["title_nl"]
    assert body["help_nl"]
    assert isinstance(body["items"], list)
    assert len(body["items"]) > 0
    assert all(
        "code" in item
        and "group" in item
        and "label_nl" in item
        and "status" in item
        and "value_nl" in item
        and "what_it_means_nl" in item
        for item in body["items"]
    )


def test_runbook_lists_paper_only_mode_as_ok_when_locked() -> None:
    api_settings.paper_only_mode = True
    body = _client().get("/runbook").json()
    items = _items_by_code(body)
    assert items["paper_only_mode"]["status"] == "ok"


def test_runbook_flags_paper_only_mode_as_blocking_when_off() -> None:
    """Hypothetical guardrail — paper_only_mode=False zou NOOIT
    mogen voorkomen in productie. De runbook MOET dit als blocking
    flaggen."""

    api_settings.paper_only_mode = False
    body = _client().get("/runbook").json()
    items = _items_by_code(body)
    assert items["paper_only_mode"]["status"] == "blocking"
    assert body["ready_for_paper_go_live"] is False
    assert "Paper-only modus" in body["summary_nl"]


# ----------------------------------------------------------------------
# Provider configuration
# ----------------------------------------------------------------------


def test_runbook_flags_storage_blocking_when_disabled() -> None:
    api_settings.paper_only_mode = True
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    body = _client().get("/runbook").json()
    items = _items_by_code(body)
    assert items["storage_writable"]["status"] == "blocking"
    assert body["ready_for_paper_go_live"] is False


def test_runbook_storage_ok_when_all_flags_set() -> None:
    api_settings.paper_only_mode = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    body = _client().get("/runbook").json()
    items = _items_by_code(body)
    assert items["storage_writable"]["status"] == "ok"


def test_runbook_warns_when_eodhd_key_missing() -> None:
    api_settings.eodhd_api_key = None
    body = _client().get("/runbook").json()
    items = _items_by_code(body)
    assert items["eodhd_api_key"]["status"] == "warning"


def test_runbook_ok_when_eodhd_key_set() -> None:
    api_settings.eodhd_api_key = "secret"
    body = _client().get("/runbook").json()
    items = _items_by_code(body)
    assert items["eodhd_api_key"]["status"] == "ok"


def test_runbook_claude_key_missing_is_info_not_blocking() -> None:
    """CLAUDE.md §15 — AI nooit verplicht; alleen NL-uitleg."""

    api_settings.claude_ai_api_key = None
    body = _client().get("/runbook").json()
    items = _items_by_code(body)
    assert items["claude_ai_api_key"]["status"] == "info"


# ----------------------------------------------------------------------
# Doctrine-features
# ----------------------------------------------------------------------


def test_runbook_features_off_show_as_warnings() -> None:
    api_settings.earnings_calendar_sync_enabled = False
    api_settings.orchestrator_scoring_enabled = False
    body = _client().get("/runbook").json()
    items = _items_by_code(body)
    assert items["earnings_calendar_sync_enabled"]["status"] == "warning"
    assert items["orchestrator_scoring_enabled"]["status"] == "warning"


def test_runbook_features_on_show_as_ok() -> None:
    api_settings.earnings_calendar_sync_enabled = True
    api_settings.orchestrator_scoring_enabled = True
    body = _client().get("/runbook").json()
    items = _items_by_code(body)
    assert items["earnings_calendar_sync_enabled"]["status"] == "ok"
    assert items["orchestrator_scoring_enabled"]["status"] == "ok"


# ----------------------------------------------------------------------
# Aggregated readiness
# ----------------------------------------------------------------------


def test_runbook_ready_when_all_doctrine_locks_pass_and_features_on() -> None:
    api_settings.paper_only_mode = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.eodhd_api_key = "secret"
    api_settings.ibkr_enabled = True
    api_settings.claude_ai_api_key = "key"
    api_settings.market_data_sync_enabled = True
    api_settings.forecast_sync_enabled = True
    api_settings.suggestions_sync_enabled = True
    api_settings.decision_packages_sync_enabled = True
    api_settings.action_drafts_sync_enabled = True
    api_settings.earnings_calendar_sync_enabled = True
    api_settings.orchestrator_scoring_enabled = True
    api_settings.daily_briefing_sync_enabled = True

    body = _client().get("/runbook").json()
    assert body["ready_for_paper_go_live"] is True
    assert "in orde" in body["summary_nl"].lower() or "klaar" in body["summary_nl"].lower()
    # No blocking items.
    assert all(item["status"] != "blocking" for item in body["items"])


def test_runbook_ready_with_warnings_when_some_features_off() -> None:
    """Doctrine-features mogen uit staan zonder hard te blokkeren —
    de operator krijgt alleen een warning dat sommige legs op
    skipped vallen."""

    api_settings.paper_only_mode = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.eodhd_api_key = "secret"
    api_settings.ibkr_enabled = True
    api_settings.market_data_sync_enabled = False  # warning

    body = _client().get("/runbook").json()
    assert body["ready_for_paper_go_live"] is True  # not blocking
    assert "warning" in body["summary_nl"].lower()


def test_runbook_summary_includes_blocking_labels() -> None:
    """Wanneer er blocking items zijn moeten de labels in de
    summary zichtbaar zijn zodat de operator snel weet wat te
    fixen."""

    api_settings.paper_only_mode = False  # blocking
    api_settings.storage.enabled = False  # blocking
    body = _client().get("/runbook").json()
    assert "Paper-only modus" in body["summary_nl"]
    assert "Opslag" in body["summary_nl"]
