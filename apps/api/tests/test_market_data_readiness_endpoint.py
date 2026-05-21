from ai_trading_agent_storage import StorageConnectionError
from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app
from portfolio_outlook_api.market_data_readiness import (
    LatestSnapshotResponse,
    LatestSnapshotStatus,
    ReadinessBlockerCode,
    ReadinessDetailResponse,
    ReadinessFreshnessStatus,
    ReadinessListResponse,
    ReadinessSnapshotMetadata,
    ReadinessStatus,
)
from portfolio_outlook_api.watchlist import STORE, WatchlistItem

client = TestClient(app)


def setup_function() -> None:
    STORE.clear()


def _item(item_id: str, *, conid: str | None, validation_status: str | None) -> WatchlistItem:
    return WatchlistItem(
        watchlist_item_id=item_id,
        symbol="AAPL",
        status="active",
        source="manual",
        created_at="2026-05-20T00:00:00Z",
        updated_at="2026-05-20T00:00:00Z",
        ibkr_conid=conid,
        ibkr_validation_status=validation_status,
    )


def _inactive_item(item_id: str) -> WatchlistItem:
    return WatchlistItem(
        watchlist_item_id=item_id,
        symbol="AAPL",
        status="inactive",
        source="manual",
        created_at="2026-05-20T00:00:00Z",
        updated_at="2026-05-20T00:00:00Z",
        ibkr_conid="265598",
        ibkr_validation_status="valid",
    )


def test_market_data_readiness_blocks_unvalidated_identity() -> None:
    STORE["w-1"] = _item("w-1", conid="265598", validation_status="unvalidated")
    STORE["w-2"] = _item("w-2", conid=None, validation_status=None)

    response = client.get("/market-data/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    for row in payload["items"]:
        assert row["status"] == "blocked"
        assert row["readiness_status"] == "blocked"
        assert row["freshness_status"] == "missing_snapshot"
        assert row["blocker_code"] == "missing_or_unvalidated_ibkr_contract"
        assert "blocker_reason_nl" in row
        assert "missing_identity_fields" in row
        assert row["snapshot_metadata_present"] is False
        assert row["latest_snapshot_metadata"] is None
        assert "geen market-data runtime" in row["audit_help_nl"].lower()
        assert "evaluated_at" in row
        assert "next_step_nl" in row
        assert "analyse" in row["blocker_reason_nl"].lower()


def test_market_data_readiness_ready_for_validated_identity_only() -> None:
    STORE["w-1"] = _item("w-1", conid="265598", validation_status="valid")

    response = client.get("/market-data/readiness")
    assert response.status_code == 200
    row = response.json()["items"][0]
    assert row["status"] == "ready"
    assert row["readiness_status"] == "ready"
    assert row["blocker_code"] is None
    assert row["freshness_status"] == "missing_snapshot"
    assert row["missing_identity_fields"] == []
    assert row["validation_status"]["ibkr_conid_present"] is True
    assert row["validation_status"]["ibkr_contract_validated"] is True
    assert "snapshot" in row["next_step_nl"].lower()


def test_market_data_readiness_excludes_inactive_items() -> None:
    STORE["w-1"] = _item("w-1", conid="265598", validation_status="valid")
    STORE["w-2"] = _inactive_item("w-2")
    response = client.get("/market-data/readiness")
    assert response.status_code == 200
    payload = ReadinessListResponse.model_validate(response.json())
    assert len(payload.items) == 1
    assert payload.items[0].watchlist_item_id == "w-1"


def test_market_data_readiness_watchlist_detail_endpoint() -> None:
    STORE["w-1"] = _item("w-1", conid="265598", validation_status="valid")
    response = client.get("/market-data/readiness/watchlist/w-1")
    assert response.status_code == 200
    assert response.json()["item"]["watchlist_item_id"] == "w-1"
    assert response.json()["item"]["audit_help_nl"]


def test_market_data_readiness_list_response_contract() -> None:
    STORE["w-1"] = _item("w-1", conid="", validation_status=None)

    response = client.get("/market-data/readiness")
    assert response.status_code == 200

    parsed = ReadinessListResponse.model_validate(response.json())
    assert parsed.help_nl
    assert parsed.items[0].status == ReadinessStatus.BLOCKED
    assert parsed.items[0].readiness_status == ReadinessStatus.BLOCKED
    assert parsed.items[0].freshness_status == ReadinessFreshnessStatus.MISSING_SNAPSHOT
    assert (
        parsed.items[0].blocker_code
        == ReadinessBlockerCode.MISSING_OR_UNVALIDATED_IBKR_CONTRACT
    )
    assert parsed.items[0].validation_status.ibkr_conid_present is False


def test_market_data_readiness_detail_response_contract_for_missing_item() -> None:
    response = client.get("/market-data/readiness/watchlist/unknown")
    assert response.status_code == 200

    parsed = ReadinessDetailResponse.model_validate(response.json())
    assert parsed.item is None
    assert parsed.message_nl == "Volglijst-item niet gevonden."


def test_market_data_snapshot_latest_returns_not_configured_when_storage_disabled() -> None:
    response = client.get("/market-data/snapshots/latest/265598")
    assert response.status_code == 200
    parsed = LatestSnapshotResponse.model_validate(response.json())
    assert parsed.ibkr_conid == "265598"
    assert parsed.status == LatestSnapshotStatus.NOT_CONFIGURED
    assert parsed.latest_snapshot_metadata is None
    assert parsed.missing_reason == "storage_not_configured"
    assert "geen" in parsed.help_nl.lower()


def test_market_data_snapshot_latest_returns_missing_snapshot_variant(monkeypatch) -> None:
    class _FakeStorageSettings:
        enabled = True
        database_url = "sqlite:///fake"

    class _FakeContext:
        def __enter__(self) -> object:
            class _Checked:
                connection = object()
                readiness = object()

            return _Checked()

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    class _GoodProvider:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def checked_connection(self, *, require_writable: bool) -> _FakeContext:
            assert require_writable is False
            return _FakeContext()

    class _FakeRepo:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def get_latest_by_ibkr_conid(self, _ibkr_conid: str) -> object:
            class _Result:
                record = None

            return _Result()

    monkeypatch.setattr(
        "portfolio_outlook_api.status_routes.settings.storage",
        _FakeStorageSettings(),
    )
    monkeypatch.setattr(
        "portfolio_outlook_api.status_routes.StorageConnectionProvider",
        _GoodProvider,
    )
    monkeypatch.setattr(
        "portfolio_outlook_api.status_routes.SqlAlchemyMarketDataSnapshotRepository", _FakeRepo
    )

    response = client.get("/market-data/snapshots/latest/265598")
    assert response.status_code == 200
    parsed = LatestSnapshotResponse.model_validate(response.json())
    assert parsed.status == LatestSnapshotStatus.MISSING_SNAPSHOT
    assert parsed.status_nl == "Nog geen snapshotmetadata opgeslagen."
    assert parsed.missing_reason == "snapshot_not_found"
    assert parsed.latest_snapshot_metadata is None


def test_market_data_snapshot_latest_returns_storage_failure_variant(monkeypatch) -> None:
    class _FakeStorageSettings:
        enabled = True
        database_url = "sqlite:///fake"

    class _FailingProvider:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def checked_connection(self, *, require_writable: bool) -> object:
            assert require_writable is False
            raise StorageConnectionError("boom")

    monkeypatch.setattr(
        "portfolio_outlook_api.status_routes.settings.storage",
        _FakeStorageSettings(),
    )
    monkeypatch.setattr(
        "portfolio_outlook_api.status_routes.StorageConnectionProvider",
        _FailingProvider,
    )

    response = client.get("/market-data/snapshots/latest/265598")
    assert response.status_code == 200
    parsed = LatestSnapshotResponse.model_validate(response.json())
    assert parsed.status == LatestSnapshotStatus.STORAGE_FAILURE
    assert parsed.blocker_reason == "storage_connection_failed"
    assert parsed.latest_snapshot_metadata is None
    assert "orders" in parsed.help_nl.lower()


def test_market_data_readiness_missing_snapshot_includes_dutch_audit_fields() -> None:
    STORE["w-1"] = _item("w-1", conid="265598", validation_status="valid")

    response = client.get("/market-data/readiness/watchlist/w-1")
    assert response.status_code == 200
    row = response.json()["item"]
    assert row["freshness_status"] == "missing_snapshot"
    assert "read-only" in row["audit_help_nl"].lower()
    assert "geen market-data runtime" in row["help_nl"].lower()
    assert "suggestie" in row["audit_help_nl"].lower()


def test_market_data_readiness_missing_conid_remains_blocked() -> None:
    STORE["w-1"] = _item("w-1", conid=None, validation_status="valid")

    response = client.get("/market-data/readiness/watchlist/w-1")
    assert response.status_code == 200
    row = response.json()["item"]
    assert row["status"] == "blocked"
    assert row["blocker_code"] == "missing_or_unvalidated_ibkr_contract"
    assert "ibkr_conid" in row["missing_identity_fields"]


def test_market_data_readiness_invalid_validation_status_is_blocked() -> None:
    STORE["w-1"] = _item("w-1", conid="265598", validation_status="invalid")
    response = client.get("/market-data/readiness/watchlist/w-1")
    assert response.status_code == 200
    parsed = ReadinessDetailResponse.model_validate(response.json())
    assert parsed.item is not None
    assert parsed.item.status == ReadinessStatus.BLOCKED
    assert (
        parsed.item.blocker_code
        == ReadinessBlockerCode.MISSING_OR_UNVALIDATED_IBKR_CONTRACT
    )


def test_market_data_readiness_stored_snapshot_metadata_is_read_only(monkeypatch) -> None:
    STORE["w-1"] = _item("w-1", conid="265598", validation_status="valid")

    def _fake_snapshot_metadata(_: str | None) -> ReadinessSnapshotMetadata | None:
        return ReadinessSnapshotMetadata(
            snapshot_id="snap-1",
            watchlist_item_id="w-1",
            asset_id=None,
            ibkr_conid="265598",
            symbol="AAPL",
            security_type="STK",
            exchange="NASDAQ",
            primary_exchange="NASDAQ",
            currency="USD",
            provider_name="manual",
            data_kind="quote_snapshot",
            captured_at="2026-05-20T00:00:00Z",
            source_timestamp="2026-05-20T00:00:00Z",
            stored_at="2026-05-20T00:01:00Z",
            freshness_status="fresh",
            validation_status="validated",
            blocked_reason=None,
            raw_reference=None,
            explanation_nl="Alleen metadata voor audit.",
        )

    monkeypatch.setattr(
        "portfolio_outlook_api.status_routes._read_snapshot_metadata",
        _fake_snapshot_metadata,
    )

    response = client.get("/market-data/readiness/watchlist/w-1")
    assert response.status_code == 200
    row = response.json()["item"]
    assert row["status"] == "ready"
    assert row["snapshot_metadata_present"] is True
    assert row["latest_snapshot_metadata"]["snapshot_id"] == "snap-1"
    assert "read-only" in row["audit_help_nl"].lower()
    assert "geen market-data runtime" in row["help_nl"].lower()
    assert "forecast" not in str(row).lower()
    assert "decision package" not in str(row).lower()
    assert "order" not in str(row).lower()
