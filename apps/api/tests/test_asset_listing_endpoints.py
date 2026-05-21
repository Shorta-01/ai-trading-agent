from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from ai_trading_agent_storage import AssetListingRecord, AssetMasterRecord, MigrationReadinessReport, MigrationReadinessStatus
from fastapi.testclient import TestClient

from portfolio_outlook_api import asset_listings
from portfolio_outlook_api.config import StorageSettings
from portfolio_outlook_api.main import app

client = TestClient(app)

@pytest.fixture
def fake_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(asset_listings.settings, 'storage', StorageSettings(enabled=True, database_url='postgresql://u:p@db/app'))

    class FakeProvider:
        def __init__(self, _s) -> None: pass
        @contextmanager
        def checked_connection(self, *, require_writable: bool) -> Iterator[object]:
            yield type('Checked', (), {'connection': object(), 'readiness': MigrationReadinessReport(status=MigrationReadinessStatus.MIGRATIONS_CURRENT,database_connected=True,migrations_checked_against_database=True,offline_inventory_valid=True,latest_expected_revision_id='0022_asset_listing_identity_foundation',database_revision_id='0022_asset_listing_identity_foundation',persistence_allowed=True,blocks_runtime_writes=False,explanation_nl='ok')})()

    class FakeRepo:
        _now = datetime.now(UTC)
        _assets={'asset-1': AssetMasterRecord(asset_id='asset-1',canonical_symbol='ASML',asset_name='ASML',asset_type='equity',primary_exchange=None,primary_currency=None,country=None,isin=None,figi=None,cusip=None,ibkr_contract_id=None,sector=None,industry=None,status='active',created_at=_now,updated_at=_now,identity_confidence='laag',identity_source='handmatig',source_reference_ids_json=None,audit_context_json=None,safe_to_use_for_suggestions=False,blocks_suggestions=True,explanation_nl='x')}
        _listings: dict[str, AssetListingRecord] = {}
        def __init__(self, _c, _r) -> None: pass
        def get_asset_by_asset_id(self, asset_id:str): return self._assets.get(asset_id)
        def save_asset_listing(self, record: AssetListingRecord): self._listings[record.listing_id]=record; return record
        def list_asset_listings(self, asset_id: str|None=None):
            rows=tuple(self._listings.values())
            return tuple(r for r in rows if asset_id is None or r.asset_id==asset_id)
        def get_asset_listing_by_listing_id(self, listing_id:str): return self._listings.get(listing_id)
        def search_asset_listings(self, query:str, limit:int=20): return self.list_asset_listings()[:limit]

    monkeypatch.setattr(asset_listings, 'StorageConnectionProvider', FakeProvider)
    monkeypatch.setattr(asset_listings, 'SqlAlchemyResearchSourceArchiveRepository', FakeRepo)


def test_create_and_read_asset_listing(fake_storage: None) -> None:
    resp = client.post('/assets/listings', json={'listing_id':'listing-1','asset_id':'asset-1','symbol':'ASML','security_type':'STK','currency':'EUR','ibkr_conid':'123'})
    assert resp.status_code == 200
    assert resp.json()['market_data_ready'] is False
    assert 'geen market-data runtime' in resp.json()['help_nl'].lower()
    assert client.get('/assets/listings/listing-1').status_code == 200
    assert len(client.get('/assets/listings').json()['records']) == 1
    assert len(client.get('/assets/listings/search', params={'q':'asml'}).json()['records']) == 1


def test_create_rejects_unknown_asset(fake_storage: None) -> None:
    resp = client.post('/assets/listings', json={'listing_id':'listing-x','asset_id':'missing','symbol':'ASML','security_type':'STK','currency':'EUR'})
    assert resp.status_code == 404
