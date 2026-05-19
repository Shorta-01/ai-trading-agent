from __future__ import annotations

from contextlib import contextmanager

from ai_trading_agent_storage import (
    StorageConnectionError,
    build_database_not_connected_readiness_report,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api.config import StorageSettings
from portfolio_outlook_api.main import app
from portfolio_outlook_api.trading_settings import build_trading_settings_response

client = TestClient(app)


class _FakeProvider:
    def __init__(self, checked_obj: object, *, tracker: dict[str, object]) -> None:
        self._checked_obj = checked_obj
        self._tracker = tracker

    @contextmanager
    def checked_connection(self, *, require_writable: bool):
        self._tracker["require_writable"] = require_writable
        if isinstance(self._checked_obj, Exception):
            raise self._checked_obj
        yield self._checked_obj


class _Checked:
    def __init__(self) -> None:
        self.connection = object()
        self.readiness = build_database_not_connected_readiness_report()


class _ReadResult:
    def __init__(self, *, found: bool, record: object | None) -> None:
        self.found = found
        self.record = record


class _Record:
    def __init__(
        self,
        allowed_universe: dict[str, object],
        user_strategy: dict[str, object],
    ) -> None:
        self.allowed_universe = allowed_universe
        self.user_strategy = user_strategy


def test_trading_settings_endpoint_storage_disabled_defaults() -> None:
    response = build_trading_settings_response(StorageSettings(enabled=False, database_url=None))

    assert response["settings_source"] == "domain_defaults"
    assert response["settings_loaded_from_storage"] is False
    assert "Opslag staat uit" in str(response["message_nl"])


def test_trading_settings_endpoint_database_url_missing_defaults() -> None:
    response = build_trading_settings_response(StorageSettings(enabled=True, database_url=""))

    assert response["settings_source"] == "domain_defaults"
    assert response["settings_loaded_from_storage"] is False
    assert "Database-url ontbreekt" in str(response["message_nl"])


def test_trading_settings_endpoint_reads_persisted_settings() -> None:
    tracker: dict[str, object] = {"provider_called": False, "repository_called": False}
    checked = _Checked()

    def provider_factory(_: object) -> _FakeProvider:
        tracker["provider_called"] = True
        return _FakeProvider(checked, tracker=tracker)

    persisted_allowed_universe = {
        "allow_etfs": False,
        "allow_stocks": True,
        "allow_currencies_watch_only": False,
        "blocked_asset_types": ["options", "futures"],
    }
    persisted_user_strategy = {
        "portfolio_goal": "income_focus",
        "risk_level": "low",
        "max_position_pct": "12.5",
        "min_cash_reserve_pct": "7.5",
        "currency_preference": "eur",
    }

    class Repo:
        def __init__(self, connection: object, readiness: object) -> None:
            tracker["repository_called"] = True
            tracker["connection"] = connection
            tracker["readiness"] = readiness

        def get_settings(self, settings_id: str) -> _ReadResult:
            tracker["settings_id"] = settings_id
            return _ReadResult(
                found=True,
                record=_Record(persisted_allowed_universe, persisted_user_strategy),
            )

    response = build_trading_settings_response(
        StorageSettings(enabled=True, database_url="postgresql://db"),
        connection_provider_factory=provider_factory,
        repository_factory=Repo,
    )

    assert tracker["provider_called"] is True
    assert tracker["repository_called"] is True
    assert tracker["require_writable"] is False
    assert tracker["connection"] is checked.connection
    assert tracker["readiness"] is checked.readiness
    assert tracker["settings_id"] == "default"

    assert response["settings_source"] == "storage"
    assert response["settings_loaded_from_storage"] is True
    assert response["allowed_universe"] == persisted_allowed_universe
    assert response["user_strategy"] == persisted_user_strategy
    assert response["always_blocked_asset_types"] == [
        "options",
        "futures",
        "leverage",
        "short_selling",
        "crypto",
        "penny_stocks",
        "cfds",
        "complex_derivatives",
    ]
    assert "Opgeslagen trading instellingen geladen" in str(response["message_nl"])


def test_trading_settings_endpoint_storage_enabled_but_no_row() -> None:
    checked = _Checked()

    def provider_factory(_: object) -> _FakeProvider:
        return _FakeProvider(checked, tracker={})

    class Repo:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def get_settings(self, _settings_id: str) -> _ReadResult:
            return _ReadResult(found=False, record=None)

    response = build_trading_settings_response(
        StorageSettings(enabled=True, database_url="postgresql://db"),
        connection_provider_factory=provider_factory,
        repository_factory=Repo,
    )

    assert response["settings_source"] == "domain_defaults"
    assert response["settings_loaded_from_storage"] is False
    assert response["storage_available"] is True
    assert "geen opgeslagen instellingen" in str(response["message_nl"]).lower()


def test_trading_settings_endpoint_connection_failure_safe_fallback() -> None:
    def provider_factory(_: object) -> _FakeProvider:
        return _FakeProvider(StorageConnectionError("boom"), tracker={})

    class Repo:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("repo should not be constructed")

    response = build_trading_settings_response(
        StorageSettings(enabled=True, database_url="postgresql://db"),
        connection_provider_factory=provider_factory,
        repository_factory=Repo,
    )

    assert response["settings_source"] == "domain_defaults"
    assert response["settings_loaded_from_storage"] is False
    assert "veilige foutafhandeling" in str(response["message_nl"]).lower()
    assert "postgresql://" not in str(response)


def test_trading_settings_endpoint_http_200_and_response_shape() -> None:
    response = client.get('/settings/trading')

    assert response.status_code == 200
    body = response.json()
    assert body['title_nl'] == 'Trading instellingen'
    assert body['help_texts']
    assert body['always_blocked_asset_types'] == [
        'options',
        'futures',
        'leverage',
        'short_selling',
        'crypto',
        'penny_stocks',
        'cfds',
        'complex_derivatives',
    ]
    assert isinstance(body['user_strategy']['max_position_pct'], str)
    assert isinstance(body['user_strategy']['min_cash_reserve_pct'], str)
