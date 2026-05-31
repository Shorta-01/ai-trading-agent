"""Tests for the concrete ``MorningAlertsRunner``.

Same in-memory-storage-stub pattern as ``test_digest_runner.py``: we
verify the runner respects the email-gating decision matrix and
gracefully degrades when data is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from portfolio_outlook_worker.config import (
    NotificationSettings,
    StorageSettings,
)
from portfolio_outlook_worker.morning_alerts_runner import MorningAlertsRunner

_NOW = datetime(2026, 6, 1, 7, 5, tzinfo=UTC)


@dataclass
class _Position:
    conid: str


@dataclass
class _Suggestion:
    ibkr_conid: str
    symbol: str
    action_label_nl: str
    confidence_label: str = "high"
    status: str = "ready"


@dataclass
class _LatestRun:
    sync_run_id: str = "sync-x"


@dataclass
class _ListResult:
    records: tuple[Any, ...]


class _FakeIbkrRepo:
    def __init__(self, *, positions: list[_Position]) -> None:
        self._positions = positions

    def get_latest_ibkr_sync_run(self) -> _LatestRun:
        return _LatestRun()

    def list_ibkr_position_snapshots(self, _id: str) -> list[_Position]:
        return list(self._positions)


class _FakeSuggestionRepo:
    def __init__(self, *, suggestions: list[_Suggestion]) -> None:
        self._suggestions = suggestions

    def list_latest_asset_suggestions_by_conids(self, _conids):
        return _ListResult(tuple(self._suggestions))


def _patch_storage(
    monkeypatch: pytest.MonkeyPatch,
    *,
    positions: list[_Position],
    suggestions: list[_Suggestion],
) -> None:
    from portfolio_outlook_worker import morning_alerts_runner as module

    class _Connection:
        connection = object()
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Connection()

        def __exit__(self, *_):
            return None

    class _Provider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    ibkr = _FakeIbkrRepo(positions=positions)
    suggestions_repo = _FakeSuggestionRepo(suggestions=suggestions)
    monkeypatch.setattr(module, "StorageConnectionProvider", _Provider)
    monkeypatch.setattr(
        module, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        module, "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: ibkr,
    )
    monkeypatch.setattr(
        module, "SqlAlchemyAssetSuggestionRepository",
        lambda *a, **k: suggestions_repo,
    )


def _build_runner(
    notifications: NotificationSettings | None = None,
) -> MorningAlertsRunner:
    return MorningAlertsRunner(
        storage_settings=StorageSettings(
            enabled=True,
            database_url="postgresql://fake",
            writes_enabled=True,
        ),
        notifications=notifications or NotificationSettings(),
        now_provider=lambda: _NOW,
    )


def test_returns_storage_unavailable_when_disabled() -> None:
    runner = MorningAlertsRunner(
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        notifications=NotificationSettings(),
    )
    result = runner.run(ibkr_account_id="DU1", scheduled_run_id="run-1")
    assert result["sent_email"] is False
    assert result["reason"] == "storage_unavailable"


def test_no_alerts_when_no_positions(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_storage(monkeypatch, positions=[], suggestions=[])
    runner = _build_runner()
    result = runner.run(ibkr_account_id="DU1", scheduled_run_id="run-1")
    assert result["alert_count"] == 0
    assert result["email"]["sent"] is False


def test_high_confidence_sell_triggers_email_when_master_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_storage(
        monkeypatch,
        positions=[_Position(conid="aapl")],
        suggestions=[
            _Suggestion(ibkr_conid="aapl", symbol="AAPL", action_label_nl="Verkopen"),
        ],
    )
    runner = _build_runner(NotificationSettings(email_enabled=True))
    result = runner.run(ibkr_account_id="DU1", scheduled_run_id="run-1")
    assert result["alert_count"] == 1
    # SMTP creds aren't filled in this fixture, so we expect the
    # incomplete-config gate to fire — but the master+trigger
    # decision matrix has already let us through.
    assert result["email"]["sent"] is False
    assert result["email"]["reason"] == "smtp_config_incomplete"


def test_email_skipped_when_master_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_storage(
        monkeypatch,
        positions=[_Position(conid="aapl")],
        suggestions=[
            _Suggestion(ibkr_conid="aapl", symbol="AAPL", action_label_nl="Verkopen"),
        ],
    )
    runner = _build_runner(NotificationSettings(email_enabled=False))
    result = runner.run(ibkr_account_id="DU1", scheduled_run_id="run-1")
    assert result["email"]["sent"] is False
    assert result["email"]["reason"] == "email_disabled"


def test_email_skipped_when_sell_trigger_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_storage(
        monkeypatch,
        positions=[_Position(conid="aapl")],
        suggestions=[
            _Suggestion(ibkr_conid="aapl", symbol="AAPL", action_label_nl="Verkopen"),
        ],
    )
    runner = _build_runner(
        NotificationSettings(
            email_enabled=True, send_on_high_confidence_sell=False
        )
    )
    result = runner.run(ibkr_account_id="DU1", scheduled_run_id="run-1")
    assert result["email"]["sent"] is False
    assert result["email"]["reason"] == "all_alerts_disabled_by_preference"


def test_chain_failure_alert_fires_even_with_no_suggestions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_storage(monkeypatch, positions=[_Position(conid="aapl")], suggestions=[])
    runner = _build_runner(NotificationSettings(email_enabled=True))
    result = runner.run(
        ibkr_account_id="DU1",
        scheduled_run_id="run-1",
        chain_failed=True,
        failure_reason_nl="Test failure.",
    )
    assert result["alert_count"] == 1
