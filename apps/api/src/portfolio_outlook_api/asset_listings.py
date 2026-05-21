from collections.abc import Callable
from datetime import UTC, datetime

from ai_trading_agent_storage import AssetListingRecord, SqlAlchemyResearchSourceArchiveRepository, StorageConnectionError, StorageConnectionProvider, StoragePersistenceBlockedError, build_database_connection_settings
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

router = APIRouter()

def _with_repository(operation: Callable[[SqlAlchemyResearchSourceArchiveRepository], dict[str, object]], *, require_writable: bool) -> dict[str, object]:
    storage_settings = settings.storage
    if not storage_settings.enabled or not storage_settings.database_url:
        raise HTTPException(status_code=503, detail="Opslag is niet verbonden. AssetListing-service is niet beschikbaar.")
    provider = StorageConnectionProvider(build_database_connection_settings(storage_settings.database_url))
    try:
        with provider.checked_connection(require_writable=require_writable) as checked:
            return operation(SqlAlchemyResearchSourceArchiveRepository(checked.connection, checked.readiness))
    except (StorageConnectionError, StoragePersistenceBlockedError) as exc:
        raise HTTPException(status_code=503, detail="Opslag is niet verbonden. AssetListing-service is niet beschikbaar.") from exc

class AssetListingCreateRequest(BaseModel):
    listing_id: str
    asset_id: str
    symbol: str
    security_type: str
    currency: str
    ibkr_conid: str | None = None

@router.post('/assets/listings')
def create_asset_listing(request: AssetListingCreateRequest) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        if repo.get_asset_by_asset_id(request.asset_id) is None:
            raise HTTPException(status_code=404, detail='Asset-identiteit niet gevonden.')
        now = datetime.now(UTC)
        record = AssetListingRecord(
            listing_id=request.listing_id, asset_id=request.asset_id, ibkr_conid=request.ibkr_conid,
            symbol=request.symbol, local_symbol=None, trading_class=None, security_type=request.security_type,
            asset_class=None, exchange=None, primary_exchange=None, currency=request.currency, listing_country=None,
            listing_status='reference_only', validation_status='unvalidated', validation_source='handmatig', validated_at=None,
            identity_confidence='laag', identity_source='handmatig', created_at=now, updated_at=now,
            source_reference_ids_json=None, audit_context_json=None, safe_to_use_for_market_data=False,
            safe_to_use_for_analysis=False, safe_to_use_for_suggestions=False, blocks_market_data=True,
            blocks_analysis=True, blocks_suggestions=True,
            explanation_nl='Dit is alleen identiteit/referentie-informatie voor een listing, zonder runtime activering.',
        )
        saved = repo.save_asset_listing(record)
        return {"record": saved, "help_nl": "Alleen identiteit/referentie. Geen market-data runtime, analyse, suggesties, acties of orders.", "audit_help_nl": "Gebruik deze basis voor auditbare contract-identiteit.", "market_data_ready": False, "analysis_ready": False, "suggestions_allowed": False, "action_drafts_allowed": False}
    return _with_repository(op, require_writable=True)

@router.get('/assets/listings')
def list_asset_listings(asset_id: str | None = None) -> dict[str, object]:
    return _with_repository(lambda repo: {"records": repo.list_asset_listings(asset_id=asset_id), "help_nl": "Identity/reference-only overzicht."}, require_writable=False)

@router.get('/assets/listings/search')
def search_asset_listings(q: str = '') -> dict[str, object]:
    return _with_repository(lambda repo: {"records": repo.search_asset_listings(q, limit=20), "help_nl": "Alleen lokale identiteit-zoekactie; geen externe fetch."}, require_writable=False)

@router.get('/assets/listings/{listing_id}')
def get_asset_listing(listing_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        row = repo.get_asset_listing_by_listing_id(listing_id)
        if row is None:
            raise HTTPException(status_code=404, detail='AssetListing niet gevonden.')
        return {"record": row, "help_nl": "Identity/reference-only detail."}
    return _with_repository(op, require_writable=False)
