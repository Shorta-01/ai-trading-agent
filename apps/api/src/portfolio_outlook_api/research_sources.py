"""Metadata-only Research Source Archive API routes."""

from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime

from ai_trading_agent_storage import (
    DatabaseConnectionSettings,
    MigrationReadinessReport,
    ResearchDocumentClassificationRecord,
    ResearchDocumentSetMemberRecord,
    ResearchDocumentSetRecord,
    ResearchSourceAssetLinkRecord,
    ResearchSourceProcessingStatusRecord,
    ResearchSourceRecord,
    ResearchUploadedFileMetadataRecord,
    ResearchUrlMetadataRecord,
    ResearchUserNoteRecord,
    SqlAlchemyResearchSourceArchiveRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from pydantic import BaseModel, Field
from sqlalchemy.engine import Connection

from portfolio_outlook_api.config import StorageSettings

ConnectionProviderFactory = Callable[[DatabaseConnectionSettings], StorageConnectionProvider]
RepositoryFactory = Callable[
    [Connection, MigrationReadinessReport],
    SqlAlchemyResearchSourceArchiveRepository,
]


def _require_id(identifier: str, field_name: str) -> str:
    value = identifier.strip()
    if value == "":
        raise ValueError(f"{field_name} moet gevuld zijn.")
    return value


class ResearchSourceInput(BaseModel):
    library_source_id: str
    source_kind: str
    status: str
    classification_status: str
    extraction_status: str
    analysis_status: str
    asset_symbol: str | None = None
    asset_name: str | None = None
    title: str
    document_type: str
    source_type: str
    source_credibility_level: str | None = None
    prompt_injection_risk_level: str | None = None
    content_hash_sha256: str | None = None
    archive_storage_uri: str | None = None
    raw_source_available: bool = False
    schema_version: str
    explanation_nl: str


class ResearchUploadedFileMetadataInput(BaseModel):
    original_file_name: str
    stored_file_name: str | None = None
    content_type: str | None = None
    file_size_bytes: int | None = Field(default=None, ge=1)
    file_hash_sha256: str | None = None
    detected_language: str | None = None
    page_count: int | None = Field(default=None, ge=1)
    uploaded_by_user: bool = True
    explanation_nl: str


class ResearchUrlMetadataInput(BaseModel):
    url: str
    normalized_url: str | None = None
    domain: str | None = None
    fetched_at: datetime | None = None
    snapshot_hash_sha256: str | None = None
    snapshot_storage_uri: str | None = None
    http_status_code: int | None = Field(default=None, ge=100, le=599)
    content_type: str | None = None
    user_supplied: bool = True
    explanation_nl: str


class ResearchUserNoteInput(BaseModel):
    asset_symbol: str | None = None
    title: str
    note_nl: str
    thesis_relevance_nl: str | None = None
    user_confidence_nl: str | None = None
    explanation_nl: str


class ResearchDocumentSetInput(BaseModel):
    document_set_id: str
    asset_symbol: str
    title: str
    set_type: str
    explanation_nl: str


class ResearchDocumentSetMemberInput(BaseModel):
    member_id: str
    library_source_id: str
    fiscal_year: int | None = None
    reporting_period: str | None = None
    sort_order: int | None = Field(default=None, ge=0)


class ResearchDocumentClassificationInput(BaseModel):
    classification_id: str
    document_type: str
    source_type: str
    confidence: str
    detected_asset_symbol: str | None = None
    detected_asset_name: str | None = None
    detected_fiscal_year: int | None = None
    detected_reporting_period: str | None = None
    detected_language: str | None = None
    needs_user_review: bool
    reason_nl: str
    schema_version: str


class ResearchSourceAssetLinkInput(BaseModel):
    link_id: str
    asset_symbol: str | None = None
    asset_name: str | None = None
    conid: str | None = None
    isin: str | None = None
    link_type: str
    mapping_confidence: str
    auto_linked: bool
    requires_user_confirmation: bool
    confirmed_by_user: bool
    reason_nl: str
    confirmed_at: datetime | None = None


class ResearchProcessingStatusInput(BaseModel):
    processing_id: str
    classification_status: str
    extraction_status: str
    analysis_status: str
    readiness_status: str
    can_be_used_in_research: bool
    can_be_used_in_suggestions: bool
    needs_user_review: bool
    blocks_suggestions: bool
    last_error_nl: str | None = None
    reason_nl: str


def _with_repo(
    storage_settings: StorageSettings,
    operation: Callable[[SqlAlchemyResearchSourceArchiveRepository], dict[str, object]],
    *,
    require_writable: bool,
    connection_provider_factory: ConnectionProviderFactory | None = None,
    repository_factory: RepositoryFactory | None = None,
) -> dict[str, object]:
    if connection_provider_factory is None:
        connection_provider_factory = StorageConnectionProvider
    if repository_factory is None:
        repository_factory = SqlAlchemyResearchSourceArchiveRepository
    if not storage_settings.enabled:
        raise HTTPException(
            status_code=503,
            detail="Opslag is niet verbonden. De onderzoeksbibliotheek is nog niet beschikbaar.",
        )
    database_url = storage_settings.database_url
    if database_url is None or database_url.strip() == "":
        raise HTTPException(
            status_code=503,
            detail="Database niet verbonden. De onderzoeksbibliotheek is nog niet beschikbaar.",
        )

    provider = connection_provider_factory(build_database_connection_settings(database_url))
    try:
        with provider.checked_connection(require_writable=require_writable) as checked:
            return operation(repository_factory(checked.connection, checked.readiness))
    except (StorageConnectionError, StoragePersistenceBlockedError):
        raise HTTPException(
            status_code=503,
            detail="Opslag is niet verbonden. De onderzoeksbibliotheek is nog niet beschikbaar.",
        )
from fastapi import APIRouter, HTTPException

from portfolio_outlook_api.config import settings

router = APIRouter()


def _ok(message_nl: str, record: dict[str, object], help_nl: str) -> dict[str, object]:
    return {"status_nl": "OK", "message_nl": message_nl, "help_nl": help_nl, "record": record}


@router.post("/research/sources")
def create_research_source(payload: ResearchSourceInput) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        now = datetime.now(UTC)
        record = ResearchSourceRecord(created_at=now, updated_at=now, archived_at=None, **payload.model_dump())
        saved = repo.save_research_source(record)
        return _ok("Onderzoeksbron opgeslagen als metadata.", asdict(saved), "Deze API slaat alleen metadata op.")
    return _with_repo(settings.storage, op, require_writable=True)

@router.get("/research/sources/{library_source_id}")
def get_research_source(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_research_source(_require_id(library_source_id, "library_source_id"))
        if found is None:
            raise HTTPException(status_code=404, detail="Onderzoeksbron niet gevonden.")
        return _ok("Onderzoeksbron gevonden.", asdict(found), "Dit is metadata zonder documentinhoud.")
    return _with_repo(settings.storage, op, require_writable=False)

@router.get("/research/sources")
def list_research_sources(asset_symbol: str | None = None, active_only: bool = False) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        if asset_symbol:
            records = repo.list_research_sources_for_asset(asset_symbol)
        elif active_only:
            records = repo.list_active_research_sources()
        else:
            records = repo.list_active_research_sources()
        return {"status_nl": "OK", "message_nl": "Onderzoeksbronnen opgehaald.", "help_nl": "Lijst bevat alleen metadatarecords.", "records": [asdict(r) for r in records]}
    return _with_repo(settings.storage, op, require_writable=False)
@router.post("/research/sources/{library_source_id}/uploaded-file-metadata")
def create_uploaded_file_metadata(library_source_id: str, payload: ResearchUploadedFileMetadataInput) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        record = ResearchUploadedFileMetadataRecord(library_source_id=_require_id(library_source_id,"library_source_id"), uploaded_at=datetime.now(UTC), **payload.model_dump())
        return _ok("Bestandsmetadata opgeslagen. Het bestand zelf wordt in deze stap niet geüpload of gelezen.", asdict(repo.save_uploaded_file_metadata(record)), "Geen upload of parsing in deze endpoint.")
    return _with_repo(settings.storage, op, require_writable=True)

@router.get("/research/sources/{library_source_id}/uploaded-file-metadata")
def get_uploaded_file_metadata(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_uploaded_file_metadata(_require_id(library_source_id,"library_source_id"))
        if found is None: raise HTTPException(status_code=404, detail="Bestandsmetadata niet gevonden.")
        return _ok("Bestandsmetadata gevonden.", asdict(found), "Geen bestandinhoud opgeslagen.")
    return _with_repo(settings.storage, op, require_writable=False)

@router.post("/research/sources/{library_source_id}/url-metadata")
def create_url_metadata(library_source_id: str, payload: ResearchUrlMetadataInput) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        record = ResearchUrlMetadataRecord(library_source_id=_require_id(library_source_id,"library_source_id"), **payload.model_dump())
        return _ok("URL-metadata opgeslagen. De URL wordt in deze stap niet opgehaald of geanalyseerd.", asdict(repo.save_url_metadata(record)), "Alleen registratie, geen netwerkverkeer.")
    return _with_repo(settings.storage, op, require_writable=True)

@router.get("/research/sources/{library_source_id}/url-metadata")
def get_url_metadata(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_url_metadata(_require_id(library_source_id,"library_source_id"))
        if found is None: raise HTTPException(status_code=404, detail="URL-metadata niet gevonden.")
        return _ok("URL-metadata gevonden.", asdict(found), "URL is niet opgehaald of geanalyseerd.")
    return _with_repo(settings.storage, op, require_writable=False)

@router.post("/research/sources/{library_source_id}/user-note")
def create_user_note(library_source_id: str, payload: ResearchUserNoteInput) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        now=datetime.now(UTC); record=ResearchUserNoteRecord(library_source_id=_require_id(library_source_id,"library_source_id"), created_at=now, updated_at=now, **payload.model_dump())
        return _ok("Gebruikersnotitie opgeslagen als onderzoeksbron. Dit is bewijs, geen handelsinstructie.", asdict(repo.save_user_note(record)), "Geen suggestie of order wordt gestart.")
    return _with_repo(settings.storage, op, require_writable=True)

@router.get("/research/sources/{library_source_id}/user-note")
def get_user_note(library_source_id: str) -> dict[str, object]:
    return _with_repo(settings.storage, lambda repo: _ok("Gebruikersnotitie gevonden.", asdict(repo.get_user_note(_require_id(library_source_id,"library_source_id")) or (_ for _ in ()).throw(HTTPException(status_code=404, detail="Notitie niet gevonden."))), "Notitie blijft bewijs, geen instructie."), require_writable=False)
@router.post("/research/document-sets")
def create_document_set(payload: ResearchDocumentSetInput) -> dict[str, object]:
    return _with_repo(settings.storage, lambda repo: _ok("Documentenset opgeslagen. Vergelijking of analyse gebeurt later.", asdict(repo.save_document_set(ResearchDocumentSetRecord(created_at=datetime.now(UTC), **payload.model_dump()))), "Alleen metadata-koppeling."), require_writable=True)

@router.get("/research/document-sets/{document_set_id}")
def get_document_set(document_set_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_document_set(_require_id(document_set_id, "document_set_id"))
        if found is None: raise HTTPException(status_code=404, detail="Documentenset niet gevonden.")
        return _ok("Documentenset gevonden.", asdict(found), "Geen analyse uitgevoerd.")
    return _with_repo(settings.storage, op, require_writable=False)

@router.post("/research/document-sets/{document_set_id}/members")
def add_document_set_member(document_set_id: str, payload: ResearchDocumentSetMemberInput) -> dict[str, object]:
    record = ResearchDocumentSetMemberRecord(document_set_id=_require_id(document_set_id,"document_set_id"), created_at=datetime.now(UTC), **payload.model_dump())
    return _with_repo(settings.storage, lambda repo: _ok("Documentset-lid opgeslagen.", asdict(repo.save_document_set_member(record)), "Alleen bronkoppeling, geen parsing."), require_writable=True)

@router.get("/research/document-sets/{document_set_id}/members")
def list_document_set_members(document_set_id: str) -> dict[str, object]:
    return _with_repo(settings.storage, lambda repo: {"status_nl":"OK","message_nl":"Documentset-leden opgehaald.","help_nl":"Alleen metadatarecords.","records":[asdict(x) for x in repo.list_document_set_members(_require_id(document_set_id,"document_set_id"))]}, require_writable=False)

app_router = router
@router.post("/research/sources/{library_source_id}/classifications")
def create_classification(library_source_id: str, payload: ResearchDocumentClassificationInput) -> dict[str, object]:
    record = ResearchDocumentClassificationRecord(library_source_id=_require_id(library_source_id,"library_source_id"), classified_at=datetime.now(UTC), **payload.model_dump())
    return _with_repo(settings.storage, lambda repo: _ok("Classificatie opgeslagen als record. Er is geen automatische classificatie uitgevoerd.", asdict(repo.save_document_classification(record)), "Geen AI-analyse uitgevoerd."), require_writable=True)

@router.get("/research/sources/{library_source_id}/classifications/latest")
def get_latest_classification(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_latest_classification(_require_id(library_source_id,"library_source_id"))
        if found is None: raise HTTPException(status_code=404, detail="Classificatie niet gevonden.")
        return _ok("Laatste classificatie gevonden.", asdict(found), "Record-only; geen automatische analyse.")
    return _with_repo(settings.storage, op, require_writable=False)

@router.post("/research/sources/{library_source_id}/asset-links")
def create_asset_link(library_source_id: str, payload: ResearchSourceAssetLinkInput) -> dict[str, object]:
    record = ResearchSourceAssetLinkRecord(library_source_id=_require_id(library_source_id,"library_source_id"), created_at=datetime.now(UTC), **payload.model_dump())
    return _with_repo(settings.storage, lambda repo: _ok("Koppeling opgeslagen. Een nieuw gevonden asset wordt nog niet automatisch aan de volglijst toegevoegd.", asdict(repo.save_source_asset_link(record)), "Geen watchlist/suggestie/IBKR-actie gestart."), require_writable=True)

@router.get("/research/sources/{library_source_id}/asset-links")
def list_asset_links_for_source(library_source_id: str) -> dict[str, object]:
    return _with_repo(settings.storage, lambda repo: {"status_nl":"OK","message_nl":"Koppelingen opgehaald.","help_nl":"Audit-link records zonder acties.","records":[asdict(x) for x in repo.list_asset_links_for_source(_require_id(library_source_id,"library_source_id"))]}, require_writable=False)

@router.get("/research/asset-links/unconfirmed-detected")
def list_unconfirmed_asset_links() -> dict[str, object]:
    return _with_repo(settings.storage, lambda repo: {"status_nl":"OK","message_nl":"Niet-bevestigde nieuw-asset koppelingen opgehaald.","help_nl":"Nog geen automatische volglijst-aanpassing.","records":[asdict(x) for x in repo.list_unconfirmed_detected_asset_links()]}, require_writable=False)

@router.post("/research/sources/{library_source_id}/processing-status")
def create_processing_status(library_source_id: str, payload: ResearchProcessingStatusInput) -> dict[str, object]:
    record = ResearchSourceProcessingStatusRecord(library_source_id=_require_id(library_source_id,"library_source_id"), checked_at=datetime.now(UTC), **payload.model_dump())
    return _with_repo(settings.storage, lambda repo: _ok("Verwerkingsstatus opgeslagen. Er is geen analyse gestart.", asdict(repo.save_processing_status(record)), "Slaat alleen status op."), require_writable=True)

@router.get("/research/sources/{library_source_id}/processing-status/latest")
def get_latest_processing_status(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_latest_processing_status(_require_id(library_source_id,"library_source_id"))
        if found is None: raise HTTPException(status_code=404, detail="Verwerkingsstatus niet gevonden.")
        return _ok("Laatste verwerkingsstatus gevonden.", asdict(found), "Geen achtergrondverwerking gestart.")
    return _with_repo(settings.storage, op, require_writable=False)
