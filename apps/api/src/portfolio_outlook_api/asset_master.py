from collections.abc import Callable
from datetime import UTC, datetime

from ai_trading_agent_storage import (
    AssetIdentifierAliasRecord,
    AssetMasterRecord,
    SqlAlchemyResearchSourceArchiveRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

router = APIRouter()


def _with_repository(
    operation: Callable[[SqlAlchemyResearchSourceArchiveRepository], dict[str, object]],
    *,
    require_writable: bool,
) -> dict[str, object]:
    storage_settings = settings.storage
    if not storage_settings.enabled:
        raise HTTPException(
            status_code=503,
            detail="Opslag is niet verbonden. De asset-identiteit service is nog niet beschikbaar.",
        )
    database_url = storage_settings.database_url
    if database_url is None or database_url.strip() == "":
        raise HTTPException(
            status_code=503,
            detail="Database niet verbonden. De asset-identiteit service is nog niet beschikbaar.",
        )

    provider = StorageConnectionProvider(build_database_connection_settings(database_url))
    try:
        with provider.checked_connection(require_writable=require_writable) as checked:
            repo = SqlAlchemyResearchSourceArchiveRepository(
                checked.connection,
                checked.readiness,
            )
            return operation(repo)
    except (StorageConnectionError, StoragePersistenceBlockedError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Opslag is niet verbonden. De asset-identiteit service is nog niet beschikbaar.",
        ) from exc


class AssetCreateRequest(BaseModel):
    asset_id: str
    canonical_symbol: str
    asset_name: str
    asset_type: str


@router.post("/assets/master")
def create_asset(request: AssetCreateRequest) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        now = datetime.now(UTC)
        record = AssetMasterRecord(
            asset_id=request.asset_id,
            canonical_symbol=request.canonical_symbol,
            asset_name=request.asset_name,
            asset_type=request.asset_type,
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
            created_at=now,
            updated_at=now,
            identity_confidence="laag",
            identity_source="handmatig",
            source_reference_ids_json=None,
            audit_context_json=None,
            safe_to_use_for_suggestions=False,
            blocks_suggestions=True,
            explanation_nl="Deze asset-identiteit is alleen referentie-informatie.",
        )
        saved = repo.save_asset_master_record(record)
        return {
            "record": saved,
            "message_nl": (
                "Dit maakt geen suggestie aan. Dit maakt geen order of IBKR-actie aan. "
                "Suggesties blijven geblokkeerd."
            ),
        }

    return _with_repository(op, require_writable=True)


@router.get("/assets/master/{asset_id}")
def get_asset(asset_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        rec = repo.get_asset_by_asset_id(asset_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="Asset niet gevonden.")
        return {
            "record": rec,
            "help_nl": "Deze asset-identiteit is alleen referentie-informatie.",
        }

    return _with_repository(op, require_writable=False)


@router.get("/assets/master")
def list_assets() -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        return {
            "records": repo.list_asset_master_records(),
            "help_nl": "Suggesties blijven geblokkeerd.",
        }

    return _with_repository(op, require_writable=False)


class AliasCreateRequest(BaseModel):
    alias_id: str
    asset_id: str
    identifier_type: str
    identifier_value: str


@router.post("/assets/master/{asset_id}/aliases")
def create_alias(asset_id: str, request: AliasCreateRequest) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        rec = AssetIdentifierAliasRecord(
            alias_id=request.alias_id,
            asset_id=asset_id,
            identifier_type=request.identifier_type,
            identifier_value=request.identifier_value,
            source="handmatig",
            confidence_level="laag",
            created_at=datetime.now(UTC),
            explanation_nl="Alias is referentie-informatie.",
        )
        return {
            "record": repo.save_asset_identifier_alias(rec),
            "help_nl": "Dit maakt geen suggestie aan.",
        }

    return _with_repository(op, require_writable=True)


@router.get("/assets/master/{asset_id}/aliases")
def list_aliases(asset_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        return {
            "records": repo.list_asset_identifier_aliases(asset_id),
            "help_nl": "Dit maakt geen order of IBKR-actie aan.",
        }

    return _with_repository(op, require_writable=False)
