from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_account_snapshot_preflight import (
    build_manual_readonly_account_snapshot_preflight_readiness,
    run_manual_readonly_account_snapshot_preflight,
)


def _settings(**updates: object) -> Settings:
    base = Settings()
    return base.model_copy(update=updates)


def test_preflight_disabled() -> None:
    result = run_manual_readonly_account_snapshot_preflight(_settings(), None)
    assert result.status == "account_snapshot_preflight_disabled"
    assert result.connect_attempted is False


def test_readiness_no_connect() -> None:
    result = build_manual_readonly_account_snapshot_preflight_readiness(_settings(), None)
    assert result.status == "account_snapshot_preflight_disabled"
    assert result.connect_attempted is False
