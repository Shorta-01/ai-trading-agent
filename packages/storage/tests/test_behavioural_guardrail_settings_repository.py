"""Task 134a — behavioural_guardrail_settings repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    BehaviouralGuardrailSettings,
    SqlAlchemyBehaviouralGuardrailSettingsRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)

_LATEST = "0052_ibkr_submission_lifecycle_audit_and_executions"
_BASE_TS = datetime(2026, 5, 26, 9, 0, tzinfo=UTC)


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id=_LATEST,
        database_revision_id=_LATEST,
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def test_default_for_account_matches_brainstorm_locked_thresholds() -> None:
    defaults = BehaviouralGuardrailSettings.default_for_account(
        ibkr_account_id="DU1234567", last_updated_at=_BASE_TS
    )
    assert defaults.daily_max_approvals == 5
    assert defaults.cooldown_seconds == 60
    assert defaults.anti_revenge_window_hours == 72
    assert defaults.anti_revenge_loss_threshold_pct == Decimal("1.0")
    assert defaults.soft_drawdown_pct == Decimal("5.0")
    assert defaults.soft_drawdown_window_days == 5
    assert defaults.hard_drawdown_pct == Decimal("10.0")
    assert defaults.hard_drawdown_window_days == 20
    assert defaults.fomo_drift_pct == Decimal("1.5")


def test_get_or_default_returns_defaults_when_no_row() -> None:
    with _conn() as conn:
        repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
            conn, _report()
        )
        result = repo.get_or_default(
            ibkr_account_id="DU1234567", now=_BASE_TS
        )
        assert result.daily_max_approvals == 5
        # No row was inserted by get_or_default — it's read-only.
        assert repo.get_for_account("DU1234567") is None


def test_upsert_inserts_new_row() -> None:
    with _conn() as conn:
        repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
            conn, _report()
        )
        custom = BehaviouralGuardrailSettings(
            ibkr_account_id="DU1234567",
            daily_max_approvals=3,
            cooldown_seconds=120,
            anti_revenge_window_hours=48,
            anti_revenge_loss_threshold_pct=Decimal("2.0"),
            soft_drawdown_pct=Decimal("4.0"),
            soft_drawdown_window_days=7,
            hard_drawdown_pct=Decimal("8.0"),
            hard_drawdown_window_days=15,
            fomo_drift_pct=Decimal("2.5"),
            last_updated_at=_BASE_TS,
        )
        repo.upsert(custom)
        fetched = repo.get_for_account("DU1234567")
        assert fetched is not None
        assert fetched.daily_max_approvals == 3
        assert fetched.cooldown_seconds == 120


def test_upsert_updates_existing_row() -> None:
    with _conn() as conn:
        repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
            conn, _report()
        )
        initial = BehaviouralGuardrailSettings.default_for_account(
            ibkr_account_id="DU1234567", last_updated_at=_BASE_TS
        )
        repo.upsert(initial)
        # Update with new cooldown.
        updated = BehaviouralGuardrailSettings(
            ibkr_account_id="DU1234567",
            daily_max_approvals=5,
            cooldown_seconds=90,
            anti_revenge_window_hours=72,
            anti_revenge_loss_threshold_pct=Decimal("1.0"),
            soft_drawdown_pct=Decimal("5.0"),
            soft_drawdown_window_days=5,
            hard_drawdown_pct=Decimal("10.0"),
            hard_drawdown_window_days=20,
            fomo_drift_pct=Decimal("1.5"),
            last_updated_at=_BASE_TS + timedelta(hours=1),
        )
        repo.upsert(updated)
        fetched = repo.get_for_account("DU1234567")
        assert fetched is not None
        assert fetched.cooldown_seconds == 90


def test_get_or_default_returns_persisted_when_row_exists() -> None:
    with _conn() as conn:
        repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
            conn, _report()
        )
        custom = BehaviouralGuardrailSettings(
            ibkr_account_id="DU1234567",
            daily_max_approvals=10,
            cooldown_seconds=30,
            anti_revenge_window_hours=72,
            anti_revenge_loss_threshold_pct=Decimal("1.0"),
            soft_drawdown_pct=Decimal("5.0"),
            soft_drawdown_window_days=5,
            hard_drawdown_pct=Decimal("10.0"),
            hard_drawdown_window_days=20,
            fomo_drift_pct=Decimal("1.5"),
            last_updated_at=_BASE_TS,
        )
        repo.upsert(custom)
        result = repo.get_or_default(
            ibkr_account_id="DU1234567", now=_BASE_TS
        )
        assert result.daily_max_approvals == 10
        assert result.cooldown_seconds == 30


def test_invalid_threshold_rejected_at_dataclass() -> None:
    with pytest.raises(ValueError):
        BehaviouralGuardrailSettings(
            ibkr_account_id="DU1234567",
            daily_max_approvals=0,  # must be > 0
            cooldown_seconds=60,
            anti_revenge_window_hours=72,
            anti_revenge_loss_threshold_pct=Decimal("1.0"),
            soft_drawdown_pct=Decimal("5.0"),
            soft_drawdown_window_days=5,
            hard_drawdown_pct=Decimal("10.0"),
            hard_drawdown_window_days=20,
            fomo_drift_pct=Decimal("1.5"),
            last_updated_at=_BASE_TS,
        )
