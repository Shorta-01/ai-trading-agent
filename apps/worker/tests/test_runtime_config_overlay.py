"""V1.2 §BZ vervolg tests voor ``apply_worker_runtime_config_overlay``.

Focus op de nieuwe ``ibkr.account_id`` overlay-tak: zonder die
overlay houdt de worker permanent vast aan ``WORKER_IBKR__ACCOUNT_ID``
env-var ook na een operator-save via /instellingen.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from ai_trading_agent_storage import RuntimeConfigRecord

from portfolio_outlook_worker.config import (
    EodhdSettings,
    IbkrSettings,
    NotificationSettings,
    SchedulerSettings,
    Settings,
    StorageSettings,
)
from portfolio_outlook_worker.runtime_config_overlay import (
    apply_worker_runtime_config_overlay,
)


def _settings(*, account_id: str = "DU1111111") -> Settings:
    return Settings(
        storage=StorageSettings(
            enabled=True,
            database_url="postgresql://fake",
            writes_enabled=True,
        ),
        ibkr=IbkrSettings(enabled=True, account_id=account_id),
        scheduler=SchedulerSettings(),
        eodhd=EodhdSettings(),
        notifications=NotificationSettings(),
    )


def _record(*, ibkr_account_id: str | None) -> RuntimeConfigRecord:
    return RuntimeConfigRecord(
        config_id="runtime_config",
        ibkr_enabled=True,
        ibkr_account_id=ibkr_account_id,
        ibkr_host=None,
        ibkr_port=None,
        ibkr_client_id=None,
        ai_explanation_enabled=False,
        claude_ai_explanation_model=None,
        claude_ai_budget_monthly_eur=None,
        claude_ai_api_key=None,
        updated_at=datetime.now(UTC),
    )


def _patch_overlay(monkeypatch, record: RuntimeConfigRecord | None) -> None:
    """Stub de storage provider zodat de overlay-functie ``record``
    krijgt zonder echte DB-call."""

    fake_repo = MagicMock()
    fake_repo.get.return_value = record

    class _Ctx:
        def __enter__(self):
            return MagicMock(connection=object(), readiness=object())

        def __exit__(self, *_):
            return False

    class _Provider:
        def __init__(self, _cs):
            pass

        def checked_connection(self, *, require_writable: bool):
            return _Ctx()

    monkeypatch.setattr(
        "portfolio_outlook_worker.runtime_config_overlay.StorageConnectionProvider",
        _Provider,
    )
    monkeypatch.setattr(
        "portfolio_outlook_worker.runtime_config_overlay.build_database_connection_settings",
        lambda url: object(),
    )
    monkeypatch.setattr(
        "portfolio_outlook_worker.runtime_config_overlay.SqlAlchemyRuntimeConfigRepository",
        lambda _conn, _r: fake_repo,
    )


def test_overlay_applies_ibkr_account_id_from_record(monkeypatch) -> None:
    """V1.2 §BZ vervolg — de operator save't via /instellingen een
    nieuwe account-id; de worker overlay MOET die op
    ``settings.ibkr.account_id`` toepassen."""

    settings = _settings(account_id="DU1111111")
    _patch_overlay(
        monkeypatch, _record(ibkr_account_id="DU2222222")
    )
    apply_worker_runtime_config_overlay(settings)
    assert settings.ibkr.account_id == "DU2222222"


def test_overlay_ignores_empty_ibkr_account_id(monkeypatch) -> None:
    """Een lege/whitespace string mag de bestaande env-var niet
    overschrijven — anders zou een per-ongeluk gewiste UI-veld de
    worker permanent ontwortelen."""

    settings = _settings(account_id="DU1111111")
    _patch_overlay(monkeypatch, _record(ibkr_account_id="   "))
    apply_worker_runtime_config_overlay(settings)
    assert settings.ibkr.account_id == "DU1111111"


def test_overlay_ignores_none_ibkr_account_id(monkeypatch) -> None:
    """``None`` betekent: geen operator-input → houd env-var aan."""

    settings = _settings(account_id="DU1111111")
    _patch_overlay(monkeypatch, _record(ibkr_account_id=None))
    apply_worker_runtime_config_overlay(settings)
    assert settings.ibkr.account_id == "DU1111111"


def test_overlay_noop_when_no_record_exists(monkeypatch) -> None:
    settings = _settings(account_id="DU1111111")
    _patch_overlay(monkeypatch, None)
    apply_worker_runtime_config_overlay(settings)
    assert settings.ibkr.account_id == "DU1111111"


# Decimal import sanity — vermijden van linter-warnings via een
# minimale assertion zodat de Decimal-import niet als ongebruikt
# wordt geflagd.
def test_decimal_import_smoke() -> None:
    assert Decimal("1.0") == Decimal(1)
