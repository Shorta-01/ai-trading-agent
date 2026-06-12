"""V1.1 end-to-end acceptance test (Slice 34).

Mirrors the V1 acceptance test (Slice 22) but pushes the V1.1
§22-surface knobs into their rebuilt-but-still-ready configuration:

* `ensemble_weight_strategy = "auto"` (inverse-Brier auto-weights)
* `predictor_backtest_enabled = True` (walk-forward + leaderboard)
* `momentum_horizon_scaled_thresholds = True` (Slice 27 rebuild)
* `qvm_sector_neutral_zscore = True` (Slice 28 rebuild)
* `mean_reversion_hurst_asymmetric_target = True` (Slice 28 rebuild)
* `universe_set = "SP500"` (locked default)

With those knobs on alongside every V1 per-leg flag, the morning
chain still runs all six legs to ``succeeded`` and the
release-readiness scorecard still reports ``status="ready"``. This
pins the V1.1 expansion queue closed — the §22 rebuild slices are
backwards-compatible with the V1 acceptance criterion.

Manual approval gate stays: safety booleans hard-False on every
response. No order leaves the chain.
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


def _enable_every_flag_with_v1_1_rebuild_knobs_on() -> None:
    # V1 per-leg flags + integrations.
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
    api_settings.reconciliation_sync_enabled = True
    api_settings.prediction_diary_sync_enabled = True
    # V1.1 §22 ready-for-production knobs.
    api_settings.ensemble_weight_strategy = "auto"
    api_settings.predictor_backtest_enabled = True
    api_settings.universe_set = "SP500"
    api_settings.ai_explanation_real_client_enabled = False
    api_settings.ai_ts_predictor_real_client_enabled = False
    # V1.1 rebuild knobs on (Slices 27 + 28).
    api_settings.momentum_horizon_scaled_thresholds = True
    api_settings.momentum_skip_week_short_horizon = True
    api_settings.mean_reversion_hurst_asymmetric_target = True
    api_settings.qvm_sector_neutral_zscore = True
    api_settings.qvm_soft_clip_composite = True
    api_settings.gbm_regime_shift_enabled = True


def _reset_every_flag() -> None:
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
    api_settings.ensemble_weight_strategy = "equal_weight"
    api_settings.predictor_backtest_enabled = False
    api_settings.universe_set = "SP500"
    api_settings.ai_explanation_real_client_enabled = False
    api_settings.ai_ts_predictor_real_client_enabled = False
    api_settings.momentum_horizon_scaled_thresholds = False
    api_settings.momentum_skip_week_short_horizon = False
    api_settings.mean_reversion_hurst_asymmetric_target = False
    api_settings.qvm_sector_neutral_zscore = False
    api_settings.qvm_soft_clip_composite = False
    api_settings.gbm_regime_shift_enabled = False


def setup_function() -> None:
    _reset_every_flag()


def teardown_function() -> None:
    _reset_every_flag()


def test_v1_1_acceptance_morning_chain_succeeds_with_rebuild_knobs_on() -> None:
    """With every per-leg flag on AND the V1.1 §22 rebuild knobs on,
    the morning chain still runs all six legs to ``succeeded``. The
    rebuild knobs are backward-compatible — they widen the predictor
    behaviour but never block the daily chain."""

    _enable_every_flag_with_v1_1_rebuild_knobs_on()
    legs = build_default_morning_chain_legs(api_settings)
    result = run_morning_chain(legs=legs)
    assert result.status == CHAIN_STATUS_SUCCEEDED
    assert result.failed_leg is None
    assert result.failure_code is None
    assert [leg.leg_name for leg in result.legs] == list(MORNING_CHAIN_LEG_NAMES)
    assert all(leg.status == LEG_STATUS_SUCCEEDED for leg in result.legs)


def test_v1_1_acceptance_release_readiness_is_ready_with_rebuild_knobs_on() -> None:
    """The release-readiness scorecard still reports ``ready`` once the
    V1.1 §22 rebuild knobs are on — the V1.1 blockers all pass:
    ensemble strategy `auto`, backtesting opted in, no real Claude
    key required (stub), universe set `SP500`."""

    _enable_every_flag_with_v1_1_rebuild_knobs_on()
    report = compute_release_readiness(api_settings)
    assert report.status == "ready"
    assert report.blockers == ()
    assert "V1.1 is klaar voor productie." in report.summary_nl


def test_v1_1_acceptance_endpoint_surfaces_ready_status() -> None:
    """Same acceptance criterion via the public endpoint. The route
    threads a budget repo through when storage is reachable; in this
    test the fake URL means the route falls back to the no-repo path
    and the scorecard still reports ``ready`` because every flag is
    on."""

    _enable_every_flag_with_v1_1_rebuild_knobs_on()
    r = client.get("/v1/release-readiness")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ready"
    assert body["blockers"] == []
    # The manual approval gate stays: a ready scorecard never authorises orders.
    assert body["safe_for_orders"] is False
    assert body["blocks_orders"] is True


def test_v1_1_acceptance_safety_booleans_never_flip_on_ready_chain() -> None:
    """V1.1 doesn't loosen the safety doctrine. With the rebuild knobs
    on and the chain ``succeeded``, the persisted records + responses
    still keep ``safe_for_orders=False``; the manual approval gate is
    the only order-authorisation surface."""

    _enable_every_flag_with_v1_1_rebuild_knobs_on()
    legs = build_default_morning_chain_legs(api_settings)
    result = run_morning_chain(legs=legs)
    api_settings.storage.writes_enabled = False
    r = client.post("/scheduler/runs/morning-chain")
    body = r.json()
    assert body["safe_for_orders"] is False
    assert body["safe_for_action_drafts"] is False
    assert result.status == CHAIN_STATUS_SUCCEEDED
