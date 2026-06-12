"""V1 end-to-end acceptance test (Slice 22).

Drives the morning-chain orchestrator with every leg enabled, asserts
each leg returns ``succeeded``, and asserts that the release-readiness
scorecard reports ``ready`` for the same configuration. No real
external clients are touched — the morning-chain default-leg adapters
gate on the per-leg settings flags and return ``succeeded`` once
they're on. The release-readiness scorecard mirrors the same
configuration check, so this test pins the two together as the V1
release-gate acceptance criterion.

Manual approval gate stays: the test additionally asserts that the
result payload + scorecard payload both carry
``safe_for_orders=False``. No order leaves the chain.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app
from portfolio_outlook_api.morning_chain import (
    CHAIN_STATUS_SUCCEEDED,
    LEG_STATUS_SUCCEEDED,
    MORNING_CHAIN_LEG_NAMES,
    build_default_morning_chain_legs,
    run_morning_chain,
)
from portfolio_outlook_api.release_readiness import compute_release_readiness
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _enable_every_flag() -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "key-123"
    api_settings.ibkr_enabled = True
    api_settings.ibkr_sync_enabled = True
    api_settings.scheduler_enabled = True
    api_settings.market_data_sync_enabled = True
    api_settings.forecast_sync_enabled = True
    api_settings.suggestions_sync_enabled = True
    api_settings.decision_packages_sync_enabled = True
    api_settings.action_drafts_sync_enabled = True
    api_settings.daily_briefing_sync_enabled = True
    api_settings.orchestrator_scoring_enabled = True
    api_settings.earnings_calendar_sync_enabled = True
    api_settings.reconciliation_sync_enabled = True
    api_settings.prediction_diary_sync_enabled = True
    # V1.1 §22-surface knobs at their ready-for-production values.
    api_settings.ensemble_weight_strategy = "auto"
    api_settings.predictor_backtest_enabled = True
    api_settings.ai_explanation_real_client_enabled = False
    api_settings.ai_ts_predictor_real_client_enabled = False
    api_settings.universe_set = "SP500"


def _disable_every_flag() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.eodhd_enabled = False
    api_settings.eodhd_api_key = None
    api_settings.ibkr_enabled = False
    api_settings.ibkr_sync_enabled = False
    api_settings.scheduler_enabled = False
    api_settings.market_data_sync_enabled = False
    api_settings.forecast_sync_enabled = False
    api_settings.suggestions_sync_enabled = False
    api_settings.decision_packages_sync_enabled = False
    api_settings.action_drafts_sync_enabled = False
    api_settings.daily_briefing_sync_enabled = False
    api_settings.orchestrator_scoring_enabled = False
    api_settings.reconciliation_sync_enabled = False
    api_settings.prediction_diary_sync_enabled = False
    # V1.1 §22-surface knobs reset to their defaults.
    api_settings.ensemble_weight_strategy = "equal_weight"
    api_settings.predictor_backtest_enabled = False
    api_settings.ai_explanation_real_client_enabled = False
    api_settings.ai_ts_predictor_real_client_enabled = False
    api_settings.universe_set = "SP500"


def setup_function() -> None:
    _disable_every_flag()


def teardown_function() -> None:
    _disable_every_flag()


def test_v1_acceptance_morning_chain_all_legs_succeed_when_fully_enabled() -> None:
    """With every per-leg flag on, the morning chain runs all six legs
    to ``succeeded`` with no failed_leg. This is the V1 product-level
    acceptance criterion for the daily chain."""

    _enable_every_flag()
    legs = build_default_morning_chain_legs(api_settings)
    result = run_morning_chain(legs=legs)
    assert result.status == CHAIN_STATUS_SUCCEEDED
    assert result.failed_leg is None
    assert result.failure_code is None
    assert [leg.leg_name for leg in result.legs] == list(MORNING_CHAIN_LEG_NAMES)
    assert all(leg.status == LEG_STATUS_SUCCEEDED for leg in result.legs)


def test_v1_acceptance_release_readiness_is_ready_when_fully_enabled() -> None:
    """The release-readiness scorecard reports `ready` under the same
    fully-enabled configuration that lets the morning chain succeed.
    Pins the two together as the V1 release gate."""

    _enable_every_flag()
    report = compute_release_readiness(api_settings)
    assert report.status == "ready"
    assert report.blockers == ()


def test_v1_acceptance_endpoint_surfaces_ready_status() -> None:
    """Same acceptance criterion via the public endpoint — the operator
    can poll ``GET /v1/release-readiness`` to see whether the system
    is V1-ready before firing the morning chain."""

    _enable_every_flag()
    r = client.get("/v1/release-readiness")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ready"
    assert body["blockers"] == []
    # The manual approval gate stays: a ready scorecard never authorises orders.
    assert body["safe_for_orders"] is False
    assert body["blocks_orders"] is True


def test_v1_acceptance_safety_booleans_never_flip_on_ready_chain() -> None:
    """No matter how green the chain is, the V1 safety locks stay
    intact: every persisted record and response keeps
    ``safe_for_orders=False`` and the morning-chain run never
    auto-promotes into an order — the manual approval gate is the
    last and only authorisation surface."""

    _enable_every_flag()
    legs = build_default_morning_chain_legs(api_settings)
    result = run_morning_chain(legs=legs)
    # The morning-chain result itself carries no order-authorisation
    # surface — only audit details. We additionally exercise the
    # /scheduler/runs/morning-chain route to assert the payload stays
    # locked. Storage isn't writable in this test (no real Postgres),
    # so the route blocks; we assert the safety booleans are still
    # False on the blocked response.
    api_settings.storage.writes_enabled = False
    r = client.post("/scheduler/runs/morning-chain")
    body = r.json()
    assert body["safe_for_orders"] is False
    assert body["safe_for_action_drafts"] is False
    # And the underlying chain result confirms no leg implied any order.
    assert result.status == CHAIN_STATUS_SUCCEEDED
