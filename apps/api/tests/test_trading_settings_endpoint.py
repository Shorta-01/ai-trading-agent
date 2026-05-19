from __future__ import annotations

from contextlib import contextmanager

from ai_trading_agent_storage import (
    StorageConnectionError,
    StoragePersistenceBlockedError,
    build_database_not_connected_readiness_report,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api.config import StorageSettings
from portfolio_outlook_api.main import app
from portfolio_outlook_api.trading_settings import (
    TradingSettingsUpdateInput,
    build_trading_settings_response,
    update_trading_settings_response,
)

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


def _valid_payload() -> dict[str, object]:
    return {
        "allowed_universe": {
            "allow_etfs": True,
            "allow_stocks": True,
            "allow_currencies_watch_only": False,
            "allow_bond_etfs": False,
            "allow_commodity_etfs": False,
        },
        "user_strategy": {
            "portfolio_goal": "balanced_growth_risk",
            "risk_level": "medium",
            "asset_mix_preference": "etf_and_stock_mix",
            "preferred_regions": ["global"],
            "preferred_sectors": [],
            "avoided_sectors": [],
            "max_position_pct": "10",
            "min_cash_reserve_pct": "5",
            "currency_preference": "eur_preferred_usd_allowed",
            "prefer_simple_belgian_tax_admin": True,
        },
    }


def test_put_trading_settings_valid_save_succeeds() -> None:
    tracker: dict[str, object] = {}
    checked = _Checked()

    def provider_factory(_: object) -> _FakeProvider:
        tracker["provider_called"] = True
        return _FakeProvider(checked, tracker=tracker)

    class Repo:
        def __init__(self, connection: object, readiness: object) -> None:
            tracker["connection"] = connection
            tracker["readiness"] = readiness

        def save_settings(self, request: object) -> None:
            tracker["settings_id"] = request.settings_id
            tracker["max_position_pct"] = request.user_strategy["max_position_pct"]

    payload = TradingSettingsUpdateInput.model_validate(_valid_payload())
    response = update_trading_settings_response(
        payload,
        StorageSettings(enabled=True, database_url="postgresql://db"),
        connection_provider_factory=provider_factory,
        repository_factory=Repo,
    )

    assert response["updated"] is True
    assert tracker["provider_called"] is True
    assert tracker["require_writable"] is True
    assert tracker["connection"] is checked.connection
    assert tracker["readiness"] is checked.readiness
    assert tracker["settings_id"] == "default"
    assert tracker["max_position_pct"] == "10"


def test_put_trading_settings_storage_disabled_blocked_and_no_provider() -> None:
    called = False

    def provider_factory(_: object) -> object:
        nonlocal called
        called = True
        return object()

    payload = TradingSettingsUpdateInput.model_validate(_valid_payload())
    response = update_trading_settings_response(
        payload,
        StorageSettings(enabled=False, database_url="postgresql://db"),
        connection_provider_factory=provider_factory,
    )

    assert response["updated"] is False
    assert "opslag staat uit" in str(response["message_nl"]).lower()
    assert called is False


def test_put_trading_settings_database_url_missing_blocked_and_no_provider() -> None:
    called = False

    def provider_factory(_: object) -> object:
        nonlocal called
        called = True
        return object()

    payload = TradingSettingsUpdateInput.model_validate(_valid_payload())
    response = update_trading_settings_response(
        payload,
        StorageSettings(enabled=True, database_url=""),
        connection_provider_factory=provider_factory,
    )

    assert response["updated"] is False
    assert "database-url ontbreekt" in str(response["message_nl"]).lower()
    assert called is False


def test_put_trading_settings_writes_blocked() -> None:
    checked = _Checked()

    def provider_factory(_: object) -> _FakeProvider:
        return _FakeProvider(checked, tracker={})

    class Repo:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def save_settings(self, _request: object) -> None:
            raise StoragePersistenceBlockedError("blocked")

    payload = TradingSettingsUpdateInput.model_validate(_valid_payload())
    response = update_trading_settings_response(
        payload,
        StorageSettings(enabled=True, database_url="postgresql://db"),
        connection_provider_factory=provider_factory,
        repository_factory=Repo,
    )
    assert response["updated"] is False
    assert "writes geblokkeerd" in str(response["message_nl"]).lower()


def test_put_trading_settings_connection_failure_safe() -> None:
    def provider_factory(_: object) -> _FakeProvider:
        return _FakeProvider(StorageConnectionError("postgresql://secret"), tracker={})

    payload = TradingSettingsUpdateInput.model_validate(_valid_payload())
    response = update_trading_settings_response(
        payload,
        StorageSettings(enabled=True, database_url="postgresql://db"),
        connection_provider_factory=provider_factory,
    )
    assert response["updated"] is False
    assert "veilige foutafhandeling" in str(response["message_nl"]).lower()
    assert "postgresql://" not in str(response)


def test_put_endpoint_rejects_float_percentages() -> None:
    invalid = _valid_payload()
    invalid["user_strategy"]["max_position_pct"] = 10.0
    response = client.put("/settings/trading", json=invalid)
    assert response.status_code == 422


def test_get_trading_settings_endpoint_http_200_and_response_shape() -> None:
    response = client.get("/settings/trading")
    assert response.status_code == 200
    body = response.json()
    assert body["title_nl"] == "Trading instellingen"
    assert isinstance(body["user_strategy"]["max_position_pct"], str)


def test_get_trading_settings_is_read_only() -> None:
    response = build_trading_settings_response(StorageSettings(enabled=False, database_url=None))
    assert response["settings_source"] == "domain_defaults"
