"""Endpoint tests for ``GET /suggestions/grid``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import suggestions_grid_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.suggestions_grid_routes import (
    settings as api_settings,
)

client = TestClient(app)


def _reset() -> None:
    api_settings.suggestions_risk_profile = "Gebalanceerd"
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _make_suggestion(
    *,
    conid: str,
    symbol: str,
    action_label: str,
    generated_at: datetime,
    valid_until: datetime,
    confidence_score: str = "0.80",
    confidence_label: str = "high",
    confidence_label_nl: str = "Hoog",
    suggestion_id: str | None = None,
    status: str = "ready",
    blocking_reason: str | None = None,
    top_driver_nl: str | None = "Sterke stijging verwacht.",
    has_position: bool = True,
):
    """Build a minimal ``AssetSuggestionRecord``-shaped duck for the
    fake repo. We don't construct the real dataclass to avoid binding
    the test to its `__post_init__` validators."""

    class _Suggestion:
        def __init__(self) -> None:
            self.suggestion_id = suggestion_id or f"sug-{conid}-{generated_at.isoformat()}"
            self.ibkr_conid = conid
            self.symbol = symbol
            self.currency = "USD"
            self.forecast_id = f"forecast-{conid}"
            self.model_code = "baseline_label_translator"
            self.model_version = "v1.0.0"
            self.generated_at = generated_at
            self.valid_until = valid_until
            self.risk_profile = "Gebalanceerd"
            self.has_position = has_position
            self.action_label = action_label
            self.action_label_nl = action_label
            self.confidence_label = confidence_label
            self.confidence_label_nl = confidence_label_nl
            self.confidence_score = Decimal(confidence_score)
            self.rationale_nl = f"{action_label}: testdata."
            self.drivers_json = ("direction_label=strong_up",)
            self.blockers_json = ()
            self.status = status
            self.blocking_reason = blocking_reason
            self.branch_reason_nl = f"Testbranch → {action_label}."
            self.downgrade_reason_nl = None
            self.top_driver_nl = top_driver_nl
            self.blocking_reason_nl = None
            self.expected_return_pct = Decimal("4.50")
            self.prob_gain_pct = Decimal("72.0")

    return _Suggestion()


def _fake_grid_storage(
    monkeypatch,
    *,
    latest_run,
    positions,
    history_records,
):
    class _Connection:
        connection = "fake"
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Connection()

        def __exit__(self, *_):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    class _ListResult:
        def __init__(self, records: list[object]) -> None:
            self.records = tuple(records)

    class _FakeIbkr:
        def get_latest_ibkr_sync_run(self):
            return latest_run

        def list_ibkr_position_snapshots(self, _id: str):
            return positions

    class _FakeSuggestionRepo:
        def list_asset_suggestions_generated_since(self, _cutoff):
            return _ListResult(history_records)

    monkeypatch.setattr(
        suggestions_grid_routes,
        "StorageConnectionProvider",
        _FakeStorageProvider,
    )
    monkeypatch.setattr(
        suggestions_grid_routes,
        "build_database_connection_settings",
        lambda _u: object(),
    )
    monkeypatch.setattr(
        suggestions_grid_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: _FakeIbkr(),
    )
    monkeypatch.setattr(
        suggestions_grid_routes,
        "SqlAlchemyAssetSuggestionRepository",
        lambda *a, **k: _FakeSuggestionRepo(),
    )


def test_grid_returns_empty_response_when_storage_disabled() -> None:
    r = client.get("/suggestions/grid")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "not_configured"
    assert body["sections"] == []
    assert body["total_item_count"] == 0
    assert body["safe_for_orders"] is False


def test_grid_returns_empty_response_when_no_history(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"

    class _LatestRun:
        sync_run_id = "ibkr-sync-x"

    _fake_grid_storage(
        monkeypatch, latest_run=_LatestRun(), positions=[], history_records=[]
    )

    r = client.get("/suggestions/grid")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "no_suggestions"
    assert body["sections"] == []


def test_grid_groups_by_section_and_orders_verkopen_first(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"

    now = datetime.now(UTC)
    valid_until = now + timedelta(hours=24)
    yesterday = now - timedelta(hours=24)

    today_kopen = _make_suggestion(
        conid="1",
        symbol="AAPL",
        action_label="Kopen",
        generated_at=now,
        valid_until=valid_until,
        has_position=False,
    )
    today_verkopen = _make_suggestion(
        conid="2",
        symbol="MSFT",
        action_label="Verkopen",
        generated_at=now,
        valid_until=valid_until,
    )
    # MSFT yesterday was Houden — today it flipped to Verkopen.
    msft_yesterday = _make_suggestion(
        conid="2",
        symbol="MSFT",
        action_label="Houden",
        generated_at=yesterday,
        valid_until=now,
        suggestion_id="sug-msft-yesterday",
    )

    class _LatestRun:
        sync_run_id = "ibkr-sync-x"

    _fake_grid_storage(
        monkeypatch,
        latest_run=_LatestRun(),
        positions=[],
        history_records=[today_kopen, today_verkopen, msft_yesterday],
    )

    r = client.get("/suggestions/grid")
    body = r.json()

    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["section_count"] == 2
    assert body["total_item_count"] == 2
    # Verkopen must come before Kopen in the section ordering.
    section_labels = [s["action_label_nl"] for s in body["sections"]]
    assert section_labels == ["Verkopen", "Kopen"]
    # MSFT's row has diff_status == "gewijzigd"; AAPL is "nieuw".
    msft_item = body["sections"][0]["items"][0]
    aapl_item = body["sections"][1]["items"][0]
    assert msft_item["symbol"] == "MSFT"
    assert msft_item["diff_status"] == "gewijzigd"
    assert msft_item["previous_action_label_nl"] == "Houden"
    assert aapl_item["diff_status"] == "nieuw"
    assert aapl_item["previous_action_label_nl"] is None
    assert body["new_count"] == 1
    assert body["changed_count"] == 1


def test_grid_omits_expired_suggestions(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"

    now = datetime.now(UTC)
    long_ago = now - timedelta(hours=30)
    just_expired = now - timedelta(minutes=5)

    expired_row = _make_suggestion(
        conid="1",
        symbol="AAPL",
        action_label="Kopen",
        generated_at=long_ago,
        valid_until=just_expired,
    )

    class _LatestRun:
        sync_run_id = "ibkr-sync-x"

    _fake_grid_storage(
        monkeypatch,
        latest_run=_LatestRun(),
        positions=[],
        history_records=[expired_row],
    )

    r = client.get("/suggestions/grid")
    body = r.json()
    assert body["status"] == "all_expired"
    assert body["sections"] == []


def test_grid_section_order_is_locked() -> None:
    order = suggestions_grid_routes.get_grid_section_order()
    labels = [label for label, _ in order]
    assert labels[0] == "Verkopen"
    assert labels[-1] == "Geblokkeerd"
    # The high-urgency sells must appear before the watchlist + avoid
    # buckets — that's the whole point of the locked ordering.
    assert labels.index("Verkopen") < labels.index("Bekijken")
    assert labels.index("Verkopen") < labels.index("Vermijden")
