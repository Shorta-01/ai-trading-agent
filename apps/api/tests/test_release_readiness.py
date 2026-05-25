"""Tests for the V1 release-readiness scorecard (Slice 22)."""

from __future__ import annotations

from types import SimpleNamespace

from portfolio_outlook_api.release_readiness import (
    BLOCKER_ACTION_DRAFTS_SYNC_DISABLED,
    BLOCKER_DAILY_BRIEFING_SYNC_DISABLED,
    BLOCKER_DECISION_PACKAGES_SYNC_DISABLED,
    BLOCKER_EODHD_API_KEY_MISSING,
    BLOCKER_EODHD_NOT_CONFIGURED,
    BLOCKER_FORECAST_SYNC_DISABLED,
    BLOCKER_IBKR_NOT_ENABLED,
    BLOCKER_IBKR_SYNC_NOT_ENABLED,
    BLOCKER_MARKET_DATA_SYNC_DISABLED,
    BLOCKER_PREDICTION_DIARY_SYNC_DISABLED,
    BLOCKER_RECONCILIATION_SYNC_DISABLED,
    BLOCKER_SCHEDULER_DISABLED,
    BLOCKER_STORAGE_NOT_CONFIGURED,
    BLOCKER_STORAGE_NOT_WRITABLE,
    BLOCKER_SUGGESTIONS_SYNC_DISABLED,
    STATUS_BLOCKED,
    STATUS_READY,
    compute_release_readiness,
    serialize_release_readiness,
)


def _settings(
    *,
    storage: object | None = None,
    eodhd_enabled: bool = False,
    eodhd_api_key: str | None = None,
    ibkr_enabled: bool = False,
    ibkr_sync_enabled: bool = False,
    scheduler_enabled: bool = False,
    market_data_sync_enabled: bool = False,
    forecast_sync_enabled: bool = False,
    suggestions_sync_enabled: bool = False,
    decision_packages_sync_enabled: bool = False,
    action_drafts_sync_enabled: bool = False,
    daily_briefing_sync_enabled: bool = False,
    reconciliation_sync_enabled: bool = False,
    prediction_diary_sync_enabled: bool = False,
) -> SimpleNamespace:
    if storage is None:
        storage = SimpleNamespace(
            enabled=False,
            database_url=None,
            writes_enabled=False,
        )
    return SimpleNamespace(
        storage=storage,
        eodhd_enabled=eodhd_enabled,
        eodhd_api_key=eodhd_api_key,
        ibkr_enabled=ibkr_enabled,
        ibkr_sync_enabled=ibkr_sync_enabled,
        scheduler_enabled=scheduler_enabled,
        market_data_sync_enabled=market_data_sync_enabled,
        forecast_sync_enabled=forecast_sync_enabled,
        suggestions_sync_enabled=suggestions_sync_enabled,
        decision_packages_sync_enabled=decision_packages_sync_enabled,
        action_drafts_sync_enabled=action_drafts_sync_enabled,
        daily_briefing_sync_enabled=daily_briefing_sync_enabled,
        reconciliation_sync_enabled=reconciliation_sync_enabled,
        prediction_diary_sync_enabled=prediction_diary_sync_enabled,
    )


def _all_ready_settings() -> SimpleNamespace:
    return _settings(
        storage=SimpleNamespace(
            enabled=True,
            database_url="postgresql://fake",
            writes_enabled=True,
        ),
        eodhd_enabled=True,
        eodhd_api_key="key-123",
        ibkr_enabled=True,
        ibkr_sync_enabled=True,
        scheduler_enabled=True,
        market_data_sync_enabled=True,
        forecast_sync_enabled=True,
        suggestions_sync_enabled=True,
        decision_packages_sync_enabled=True,
        action_drafts_sync_enabled=True,
        daily_briefing_sync_enabled=True,
        reconciliation_sync_enabled=True,
        prediction_diary_sync_enabled=True,
    )


# ---- compute_release_readiness ----------------------------------------


def test_default_settings_yields_every_blocker() -> None:
    report = compute_release_readiness(_settings())
    assert report.status == STATUS_BLOCKED
    # Every check must fail when settings are at their default off state.
    assert set(report.blockers) == {
        BLOCKER_STORAGE_NOT_CONFIGURED,
        BLOCKER_STORAGE_NOT_WRITABLE,
        BLOCKER_EODHD_NOT_CONFIGURED,
        BLOCKER_EODHD_API_KEY_MISSING,
        BLOCKER_IBKR_NOT_ENABLED,
        BLOCKER_IBKR_SYNC_NOT_ENABLED,
        BLOCKER_SCHEDULER_DISABLED,
        BLOCKER_MARKET_DATA_SYNC_DISABLED,
        BLOCKER_FORECAST_SYNC_DISABLED,
        BLOCKER_SUGGESTIONS_SYNC_DISABLED,
        BLOCKER_DECISION_PACKAGES_SYNC_DISABLED,
        BLOCKER_ACTION_DRAFTS_SYNC_DISABLED,
        BLOCKER_DAILY_BRIEFING_SYNC_DISABLED,
        BLOCKER_RECONCILIATION_SYNC_DISABLED,
        BLOCKER_PREDICTION_DIARY_SYNC_DISABLED,
    }
    assert all(not c.passed for c in report.checks)


def test_all_flags_on_yields_ready_with_no_blockers() -> None:
    report = compute_release_readiness(_all_ready_settings())
    assert report.status == STATUS_READY
    assert report.blockers == ()
    assert all(c.passed for c in report.checks)
    assert "klaar voor productie" in report.summary_nl


def test_missing_eodhd_api_key_is_a_blocker_even_when_provider_enabled() -> None:
    report = compute_release_readiness(
        _settings(
            storage=SimpleNamespace(
                enabled=True, database_url="x", writes_enabled=True
            ),
            eodhd_enabled=True,
            eodhd_api_key=None,
        )
    )
    assert BLOCKER_EODHD_API_KEY_MISSING in report.blockers
    assert BLOCKER_EODHD_NOT_CONFIGURED not in report.blockers


def test_scheduler_disabled_blocker_is_present_when_flag_off() -> None:
    settings = _all_ready_settings()
    settings.scheduler_enabled = False
    report = compute_release_readiness(settings)
    assert report.status == STATUS_BLOCKED
    assert BLOCKER_SCHEDULER_DISABLED in report.blockers


def test_morning_chain_flags_independently_surface_as_blockers() -> None:
    settings = _all_ready_settings()
    settings.forecast_sync_enabled = False
    settings.suggestions_sync_enabled = False
    report = compute_release_readiness(settings)
    assert report.status == STATUS_BLOCKED
    assert BLOCKER_FORECAST_SYNC_DISABLED in report.blockers
    assert BLOCKER_SUGGESTIONS_SYNC_DISABLED in report.blockers
    # Other morning-chain flags still pass.
    assert BLOCKER_MARKET_DATA_SYNC_DISABLED not in report.blockers
    assert BLOCKER_DAILY_BRIEFING_SYNC_DISABLED not in report.blockers


def test_audit_path_flags_surface_independently() -> None:
    settings = _all_ready_settings()
    settings.reconciliation_sync_enabled = False
    report = compute_release_readiness(settings)
    assert report.status == STATUS_BLOCKED
    assert BLOCKER_RECONCILIATION_SYNC_DISABLED in report.blockers
    assert BLOCKER_PREDICTION_DIARY_SYNC_DISABLED not in report.blockers


def test_missing_storage_attribute_yields_storage_blocker_only_once() -> None:
    # Settings without a `storage` attribute should still surface the
    # storage blocker rather than crashing.
    settings = SimpleNamespace(
        eodhd_enabled=False,
        eodhd_api_key=None,
        ibkr_enabled=False,
        ibkr_sync_enabled=False,
        scheduler_enabled=False,
        market_data_sync_enabled=False,
        forecast_sync_enabled=False,
        suggestions_sync_enabled=False,
        decision_packages_sync_enabled=False,
        action_drafts_sync_enabled=False,
        daily_briefing_sync_enabled=False,
        reconciliation_sync_enabled=False,
        prediction_diary_sync_enabled=False,
    )
    report = compute_release_readiness(settings)
    storage_checks = [c for c in report.checks if c.code == BLOCKER_STORAGE_NOT_CONFIGURED]
    assert len(storage_checks) == 1
    assert not storage_checks[0].passed


# ---- serialize_release_readiness --------------------------------------


def test_serialize_ready_report_keeps_safety_booleans_false() -> None:
    report = compute_release_readiness(_all_ready_settings())
    payload = serialize_release_readiness(report)
    assert payload["status"] == "ready"
    assert payload["blockers"] == []
    assert payload["safe_for_action_drafts"] is False
    assert payload["safe_for_orders"] is False
    assert payload["blocks_orders"] is True
    assert isinstance(payload["checks"], list)
    assert all(set(check.keys()) == {"code", "passed", "detail_nl"} for check in payload["checks"])  # type: ignore[union-attr]


def test_serialize_blocked_report_lists_every_blocker() -> None:
    report = compute_release_readiness(_settings())
    payload = serialize_release_readiness(report)
    assert payload["status"] == "blocked"
    assert len(payload["blockers"]) >= 10
    # Safety booleans never flip even when the scorecard is fully blocked.
    assert payload["safe_for_orders"] is False
