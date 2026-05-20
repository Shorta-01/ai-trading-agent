from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from ai_trading_agent_storage import (
    AssetMasterRecord,
    MigrationReadinessReport,
    MigrationReadinessStatus,
    SourceToAssetLinkRecord,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api import asset_master
from portfolio_outlook_api.config import StorageSettings
from portfolio_outlook_api.main import app

client = TestClient(app)


@pytest.fixture
def fake_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        asset_master.settings,
        "storage",
        StorageSettings(enabled=True, database_url="postgresql://user:pass@db/app"),
    )

    class FakeProvider:
        def __init__(self, _settings) -> None:
            pass

        @contextmanager
        def checked_connection(self, *, require_writable: bool) -> Iterator[object]:
            readiness = MigrationReadinessReport(
                status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
                database_connected=True,
                migrations_checked_against_database=True,
                offline_inventory_valid=True,
                latest_expected_revision_id="0019",
                database_revision_id="0019",
                persistence_allowed=True,
                blocks_runtime_writes=False,
                explanation_nl="ok",
            )
            yield type("Checked", (), {"connection": object(), "readiness": readiness})()

    class FakeRepo:
        _now = datetime.now(UTC)
        _assets = {
                "asset-1": AssetMasterRecord(
                    asset_id="asset-1",
                    canonical_symbol="ASML",
                    asset_name="ASML",
                    asset_type="equity",
                    primary_exchange=None,
                    primary_currency=None,
                    country=None,
                    isin=None,
                    figi=None,
                    cusip=None,
                    ibkr_contract_id=None,
                    sector=None,
                    industry=None,
                    status="active",
                    created_at=_now,
                    updated_at=_now,
                    identity_confidence="laag",
                    identity_source="handmatig",
                    source_reference_ids_json=None,
                    audit_context_json=None,
                    safe_to_use_for_suggestions=False,
                    blocks_suggestions=True,
                    explanation_nl="x",
                )
            }
        _links: dict[str, list[SourceToAssetLinkRecord]] = defaultdict(list)

        def __init__(self, _c, _r) -> None:
            pass

        def get_asset_by_asset_id(self, asset_id: str) -> AssetMasterRecord | None:
            return self._assets.get(asset_id)

        def save_source_to_asset_link(
            self, record: SourceToAssetLinkRecord
        ) -> SourceToAssetLinkRecord:
            self._links[record.asset_id].append(record)
            return record

        def list_source_to_asset_links_for_asset(
            self, asset_id: str
        ) -> tuple[SourceToAssetLinkRecord, ...]:
            return tuple(self._links[asset_id])

    monkeypatch.setattr(asset_master, "StorageConnectionProvider", FakeProvider)
    monkeypatch.setattr(asset_master, "SqlAlchemyResearchSourceArchiveRepository", FakeRepo)


def test_create_and_list_source_to_asset_links(fake_storage: None) -> None:
    create = client.post(
        "/assets/master/source-links",
        json={
            "link_id": "l1",
            "asset_id": "asset-1",
            "target_type": "research_source",
            "target_id": "src-1",
            "link_reason_nl": "Handmatige koppeling",
            "created_by": "tester",
        },
    )
    assert create.status_code == 200
    body = create.json()
    assert body["record"]["safe_to_use_for_suggestions"] is False
    assert body["record"]["blocks_suggestions"] is True
    assert "geen suggestie" in body["help_nl"].lower()

    listed = client.get("/assets/master/asset-1/source-links")
    assert listed.status_code == 200
    assert len(listed.json()["records"]) == 1


def test_create_source_to_asset_link_fails_for_unknown_asset(fake_storage: None) -> None:
    create = client.post(
        "/assets/master/source-links",
        json={
            "link_id": "l2",
            "asset_id": "missing",
            "target_type": "research_source",
            "target_id": "src-1",
            "link_reason_nl": "Handmatige koppeling",
            "created_by": "tester",
        },
    )
    assert create.status_code == 404
