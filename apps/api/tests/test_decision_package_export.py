"""Tests for the Decision Package Markdown export."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from portfolio_outlook_api.decision_package_export import (
    export_filename,
    render_decision_packages_markdown,
)
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_GEN_AT = datetime(2026, 5, 28, 9, 30, 15, tzinfo=UTC)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _package() -> dict[str, object]:
    return {
        "decision_package_id": "dp-1",
        "content_hash": "abc123hash",
        "ibkr_conid": "265598",
        "symbol": "AAPL",
        "currency": "USD",
        "generated_at": "2026-05-28T07:00:00+00:00",
        "valid_until": "2026-06-25T07:00:00+00:00",
        "market_last_price": "190.250000",
        "forecast_horizon_days": 28,
        "forecast_p10_price": "180.000000",
        "forecast_p50_price": "195.000000",
        "forecast_p90_price": "210.000000",
        "forecast_prob_gain": "0.620000",
        "forecast_prob_loss": "0.120000",
        "forecast_expected_return_pct": "0.034000",
        "forecast_expected_volatility_annual": "0.250000",
        "forecast_downside_risk_score": "0.180000",
        "forecast_confidence_score": "0.910000",
        "forecast_model_code": "historical_bootstrap_v1",
        "forecast_model_version": "1.0.0",
        "suggestion_id": "sug-1",
        "suggestion_action_label": "BUY",
        "suggestion_action_label_nl": "Kopen",
        "suggestion_confidence_label_nl": "Hoog",
        "has_position": True,
        "gate_outcomes": ["forecast_valid: pass", "data_fresh: pass"],
        "evidence_links": ["snap-1"],
        "audit_links": ["audit://chain/1", "audit://chain/2"],
        "rationale_nl": "Sterk opwaarts signaal met verse marktdata.",
        "explanation_nl": "De voorspelling wijst op een verwacht rendement boven de drempel.",
        "research_evidence_count": 3,
        "research_credibility_summary": "Hoog",
        "research_freshness_status": "fresh",
        "research_snippet_nl": "Analisten verhoogden hun koersdoel.",
    }


# ---- export_filename --------------------------------------------------


def test_export_filename_uses_timestamp() -> None:
    assert export_filename(_GEN_AT) == "suggesties-export-20260528-093015.md"


# ---- render_decision_packages_markdown (empty) ------------------------


def test_render_empty_is_valid_markdown_with_status() -> None:
    md = render_decision_packages_markdown(
        [],
        generated_at=_GEN_AT,
        risk_profile="Gebalanceerd",
        status_nl="Geen posities",
    )
    assert "# Portfolio Outlook — Suggesties" in md
    assert "**Aantal suggesties:** 0" in md
    assert "**Risicoprofiel:** Gebalanceerd" in md
    assert "Geen posities" in md
    # The safety disclaimer is always present.
    assert "Geen beleggingsadvies" in md


# ---- render_decision_packages_markdown (populated) --------------------


def test_render_includes_action_why_forecast_and_traceability() -> None:
    md = render_decision_packages_markdown(
        [_package()],
        generated_at=_GEN_AT,
        risk_profile="Gebalanceerd",
    )
    # Header + count.
    assert "**Aantal suggesties:** 1" in md
    # Buy/sell action is prominent (Dutch label + raw code).
    assert "## 1. AAPL — Kopen" in md
    assert "**Actie:** Kopen (`BUY`)" in md
    assert "**Vertrouwen:** Hoog" in md
    assert "**Heeft positie:** Ja" in md
    # The "why" — both the short rationale and the full explanation.
    assert "Sterk opwaarts signaal met verse marktdata." in md
    assert "De voorspelling wijst op een verwacht rendement boven de drempel." in md
    # Forecast numbers carried verbatim.
    assert "180.000000 / 195.000000 / 210.000000" in md
    assert "0.910000" in md
    # Gate outcomes rendered as bullets.
    assert "- forecast_valid: pass" in md
    # Traceability: content hash + audit links.
    assert "`abc123hash`" in md
    assert "audit://chain/1" in md
    assert "audit://chain/2" in md


def test_render_missing_optional_fields_uses_em_dash() -> None:
    sparse: dict[str, object] = {
        "symbol": "MSFT",
        "suggestion_action_label_nl": "Houden",
        "suggestion_action_label": "HOLD",
    }
    md = render_decision_packages_markdown(
        [sparse], generated_at=_GEN_AT, risk_profile=None
    )
    assert "## 1. MSFT — Houden" in md
    assert "**Risicoprofiel:** —" in md
    # Empty rationale/explanation collapse to an em dash, not "None".
    assert "None" not in md


# ---- GET /decision-packages/export -----------------------------------


def test_export_route_serves_downloadable_markdown_when_storage_off() -> None:
    r = client.get("/decision-packages/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    disposition = r.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert "suggesties-export-" in disposition
    assert ".md" in disposition
    # Body is a valid, self-explanatory document even with storage off.
    assert "# Portfolio Outlook — Suggesties" in r.text
    assert "Opslag niet geconfigureerd" in r.text
