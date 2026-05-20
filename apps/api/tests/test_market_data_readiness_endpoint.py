from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app
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


def test_market_data_readiness_watchlist_detail_endpoint() -> None:
    STORE["w-1"] = _item("w-1", conid="265598", validation_status="valid")
    response = client.get("/market-data/readiness/watchlist/w-1")
    assert response.status_code == 200
    assert response.json()["item"]["watchlist_item_id"] == "w-1"
    assert response.json()["item"]["audit_help_nl"]


def test_market_data_snapshot_latest_returns_not_configured_when_storage_disabled() -> None:
    response = client.get("/market-data/snapshots/latest/265598")
    assert response.status_code == 200
    assert response.json()["item"] is None


def test_market_data_readiness_missing_snapshot_includes_dutch_audit_fields() -> None:
    STORE["w-1"] = _item("w-1", conid="265598", validation_status="valid")

    response = client.get("/market-data/readiness/watchlist/w-1")
    assert response.status_code == 200
    row = response.json()["item"]
    assert row["freshness_status"] == "missing_snapshot"
    assert "read-only" in row["audit_help_nl"].lower()
    assert "geen market-data runtime" in row["help_nl"].lower()
    assert "suggestie" in row["audit_help_nl"].lower()
