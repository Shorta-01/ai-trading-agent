from collections.abc import Callable
from datetime import UTC, datetime

from ai_trading_agent_storage import (
    AssetIdentifierAliasRecord,
    AssetMasterRecord,
    SourceToAssetLinkRecord,
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




class AssetMasterSearchRecord(BaseModel):
    asset_id: str
    canonical_symbol: str
    asset_name: str
    primary_exchange: str | None
    primary_currency: str | None
    asset_type: str
    status: str
    identifier_summary_nl: str


def _identifier_summary(record: AssetMasterRecord) -> str:
    identifiers: list[str] = []
    if record.isin:
        identifiers.append(f"ISIN: {record.isin}")
    if record.figi:
        identifiers.append(f"FIGI: {record.figi}")
    if record.cusip:
        identifiers.append(f"CUSIP: {record.cusip}")
    if record.ibkr_contract_id is not None:
        identifiers.append(f"IBKR contract: {record.ibkr_contract_id}")
    return ", ".join(identifiers) if identifiers else "Geen extra identifiers beschikbaar."


@router.get("/assets/master/search")
def search_assets(q: str = "") -> dict[str, object]:
    query = q.strip().lower()

    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        records = repo.list_asset_master_records()
        matches: list[AssetMasterSearchRecord] = []
        for rec in records:
            haystack_values = [
                rec.asset_id,
                rec.canonical_symbol,
                rec.asset_name,
                rec.primary_exchange or "",
                rec.primary_currency or "",
                rec.asset_type,
                rec.status,
                rec.isin or "",
                rec.figi or "",
                rec.cusip or "",
            ]
            if query and not any(query in value.lower() for value in haystack_values):
                continue
            matches.append(
                AssetMasterSearchRecord(
                    asset_id=rec.asset_id,
                    canonical_symbol=rec.canonical_symbol,
                    asset_name=rec.asset_name,
                    primary_exchange=rec.primary_exchange,
                    primary_currency=rec.primary_currency,
                    asset_type=rec.asset_type,
                    status=rec.status,
                    identifier_summary_nl=_identifier_summary(rec),
                )
            )
            if len(matches) >= 20:
                break

        return {
            "records": matches,
            "help_nl": (
                "Kies een bestaande asset-identiteit. "
                "Dit maakt geen suggestie, order of portfolio-positie aan."
            ),
        }

    return _with_repository(op, require_writable=False)

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


class SourceToAssetLinkCreateRequest(BaseModel):
    link_id: str
    asset_id: str
    target_type: str
    target_id: str
    link_reason_nl: str
    created_by: str
    audit_context_json: dict[str, str] | None = None


@router.post("/assets/master/source-links")
def create_source_to_asset_link(request: SourceToAssetLinkCreateRequest) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        if repo.get_asset_by_asset_id(request.asset_id) is None:
            raise HTTPException(status_code=404, detail="Asset-identiteit niet gevonden.")
        record = SourceToAssetLinkRecord(
            link_id=request.link_id,
            asset_id=request.asset_id,
            target_type=request.target_type,
            target_id=request.target_id,
            link_reason_nl=request.link_reason_nl,
            audit_context_json=request.audit_context_json,
            safe_to_use_for_suggestions=False,
            blocks_suggestions=True,
            created_at=datetime.now(UTC),
            created_by=request.created_by,
            explanation_nl="Deze link is alleen voor audit en referentie.",
        )
        saved = repo.save_source_to_asset_link(record)
        return {
            "record": saved,
            "help_nl": (
                "Deze link is alleen audit/referentie. Dit maakt geen suggestie, order, "
                "watchlist-item of IBKR-actie aan."
            ),
        }

    return _with_repository(op, require_writable=True)


@router.get("/assets/master/{asset_id}/source-links")
def list_source_to_asset_links(asset_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        return {
            "records": repo.list_source_to_asset_links_for_asset(asset_id),
            "help_nl": "Audit/referentie-links; suggesties en orders blijven geblokkeerd.",
        }

    return _with_repository(op, require_writable=False)
