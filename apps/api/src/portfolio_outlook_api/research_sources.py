"""Metadata-only Research Source Archive API routes."""

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from ai_trading_agent_storage import (
    DatabaseConnectionSettings,
    MigrationReadinessReport,
    ResearchDocumentClassificationRecord,
    ResearchDocumentSetMemberRecord,
    ResearchDocumentSetRecord,
    ResearchExtractedTextRecord,
    ResearchSourceAssetLinkRecord,
    ResearchSourceCredibilityAssessmentRecord,
    ResearchSourceEvidenceItemRecord,
    ResearchSourcePromptInjectionScanRecord,
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
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from portfolio_outlook_domain.research_library import (
    ResearchLibrarySourceKind,
    classify_document_deterministically,
)
from pydantic import BaseModel, Field
from sqlalchemy.engine import Connection

from portfolio_outlook_api.config import (
    ResearchExtractionSettings,
    ResearchUploadSettings,
    StorageSettings,
    settings,
)

ConnectionProviderFactory = Callable[[DatabaseConnectionSettings], StorageConnectionProvider]
RepositoryFactory = Callable[
    [Connection, MigrationReadinessReport],
    SqlAlchemyResearchSourceArchiveRepository,
]

router = APIRouter()
app_router = router


@dataclass(frozen=True)
class PlainTextExtractionResult:
    text_hash_sha256: str
    character_count: int
    line_count: int
    preview_text_nl: str
    extracted_text_storage_uri: str


def _require_id(identifier: str, field_name: str) -> str:
    value = identifier.strip()
    if value == "":
        raise ValueError(f"{field_name} moet gevuld zijn.")
    return value


def _ok(message_nl: str, record: dict[str, object], help_nl: str) -> dict[str, object]:
    return {
        "status_nl": "OK",
        "message_nl": message_nl,
        "help_nl": help_nl,
        "record": record,
    }


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




class ResearchSourceCredibilityAssessmentInput(BaseModel):
    assessment_id: str
    credibility_status: str
    credibility_level: str
    source_category: str
    confidence_level: str
    credibility_signals: list[str] = Field(default_factory=list)
    limitation_notes_nl: str | None = None
    safe_to_use_as_evidence: bool = False
    safe_to_use_for_suggestions: bool = False
    blocks_suggestions: bool = True
    assessed_at: datetime | None = None
    explanation_nl: str


class ResearchSourceEvidenceItemInput(BaseModel):
    evidence_item_id: str
    evidence_type: str
    evidence_status: str
    extracted_from_kind: str
    source_reference_text: str
    normalized_evidence_text: str
    evidence_summary_nl: str
    asset_symbol: str | None = None
    reporting_period: str | None = None
    fiscal_year: int | None = None
    confidence_level: str
    extraction_method: str
    source_text_hash_sha256: str | None = None
    extraction_run_id: str | None = None
    extracted_at: datetime | None = None
    safe_to_use_as_evidence: bool = False
    safe_to_use_for_suggestions: bool = False
    blocks_suggestions: bool = True
    explanation_nl: str


class ResearchPromptInjectionScanInput(BaseModel):
    scan_id: str
    scan_status: str
    risk_level: str
    detected_signals: list[str] = Field(default_factory=list)
    safe_to_use_as_evidence: bool
    safe_to_use_as_instruction: bool
    blocks_suggestions: bool = True
    scanned_at: datetime | None = None
    explanation_nl: str


def _sanitize_upload_filename(filename: str) -> str:
    cleaned = filename.strip()
    if cleaned == "":
        raise HTTPException(status_code=400, detail="Bestandsnaam ontbreekt.")
    if any(sep in cleaned for sep in ("/", "\\")) or ".." in cleaned:
        raise HTTPException(status_code=400, detail="Ongeldige bestandsnaam.")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", cleaned).strip("._")
    if safe == "":
        raise HTTPException(status_code=400, detail="Bestandsnaam is ongeldig.")
    return safe


def _default_document_type(original_name: str) -> str:
    suffix = Path(original_name).suffix.lower()
    if suffix == "":
        return "unknown_document"
    return suffix.lstrip(".")


def _archive_uploaded_file(
    *,
    upload: UploadFile,
    library_source_id: str,
    upload_settings: ResearchUploadSettings,
) -> tuple[str, str, int, str, str]:
    original_name = _sanitize_upload_filename(upload.filename or "")
    extension = Path(original_name).suffix.lower()
    if extension not in {ext.lower() for ext in upload_settings.allowed_extensions}:
        raise HTTPException(status_code=400, detail="Bestandstype is niet toegestaan.")
    content_type = (upload.content_type or "").strip().lower()
    if content_type not in {ct.lower() for ct in upload_settings.allowed_content_types}:
        raise HTTPException(status_code=400, detail="Content-Type is niet toegestaan.")

    archive_dir = Path(upload_settings.archive_dir).resolve()
    archive_dir.mkdir(parents=True, exist_ok=True)
    hasher = sha256()
    size = 0
    chunks: list[bytes] = []
    while True:
        chunk = upload.file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > upload_settings.max_file_size_bytes:
            raise HTTPException(status_code=413, detail="Bestand is te groot.")
        hasher.update(chunk)
        chunks.append(chunk)
    file_hash = hasher.hexdigest()
    stored_name = f"{library_source_id}-{file_hash[:16]}-{original_name}"
    if any(sep in stored_name for sep in ("/", "\\")) or stored_name.strip() == "":
        raise HTTPException(status_code=400, detail="Opslagbestandsnaam is ongeldig.")
    target = (archive_dir / stored_name).resolve()
    if archive_dir not in target.parents:
        raise HTTPException(status_code=400, detail="Bestandspad is ongeldig.")
    if target.exists():
        raise HTTPException(status_code=409, detail="Bestand bestaat al in archief.")
    with target.open("wb") as fh:
        for chunk in chunks:
            fh.write(chunk)
    return original_name, stored_name, size, file_hash, f"file://{target}"


def _extract_plain_research_text(
    *,
    source_archive_uri: str,
    original_filename: str,
    library_source_id: str,
    upload_settings: ResearchUploadSettings,
    extraction_settings: ResearchExtractionSettings,
) -> PlainTextExtractionResult:
    upload_root = Path(upload_settings.archive_dir).resolve()
    raw_path = Path(source_archive_uri.removeprefix("file://")).resolve()
    if upload_root not in raw_path.parents:
        raise HTTPException(status_code=400, detail="Archiefpad van bronbestand is onveilig.")
    if not raw_path.exists() or not raw_path.is_file():
        raise HTTPException(status_code=404, detail="Gearchiveerd bronbestand niet gevonden.")
    extension = Path(original_filename).suffix.lower()
    if extension not in {ext.lower() for ext in extraction_settings.allowed_extensions}:
        raise HTTPException(status_code=400, detail="Bestandstype wordt nog niet ondersteund.")
    file_size = raw_path.stat().st_size
    if file_size > extraction_settings.max_input_file_size_bytes:
        raise HTTPException(status_code=413, detail="Bestand is te groot voor extractie.")
    raw_bytes = raw_path.read_bytes()
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Bestand kon niet als UTF-8 tekst worden gelezen.",
        ) from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(normalized) > extraction_settings.max_output_characters:
        normalized = normalized[: extraction_settings.max_output_characters]
    normalized_bytes = normalized.encode("utf-8")
    text_hash = sha256(normalized_bytes).hexdigest()
    output_root = Path(extraction_settings.extracted_text_archive_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output_name = f"{library_source_id}-{text_hash[:16]}.txt"
    output_path = (output_root / output_name).resolve()
    if output_root not in output_path.parents:
        raise HTTPException(status_code=400, detail="Extractie-opslagpad is onveilig.")
    if not output_path.exists():
        output_path.write_bytes(normalized_bytes)
    return PlainTextExtractionResult(
        text_hash_sha256=text_hash,
        character_count=len(normalized),
        line_count=normalized.count("\n") + (1 if normalized else 0),
        preview_text_nl=normalized[: extraction_settings.preview_max_characters],
        extracted_text_storage_uri=f"file://{output_path}",
    )


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
    except (StorageConnectionError, StoragePersistenceBlockedError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Opslag is niet verbonden. De onderzoeksbibliotheek is nog niet beschikbaar.",
        ) from exc


@router.post("/research/sources")
def create_research_source(payload: ResearchSourceInput) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        now = datetime.now(UTC)
        record = ResearchSourceRecord(
            created_at=now,
            updated_at=now,
            archived_at=None,
            **payload.model_dump(),
        )
        saved = repo.save_research_source(record)
        return _ok(
            "Onderzoeksbron opgeslagen als metadata.",
            asdict(saved),
            "Deze API slaat alleen metadata op.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/sources/{library_source_id}")
def get_research_source(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_research_source(_require_id(library_source_id, "library_source_id"))
        if found is None:
            raise HTTPException(status_code=404, detail="Onderzoeksbron niet gevonden.")
        return _ok(
            "Onderzoeksbron gevonden.",
            asdict(found),
            "Dit is metadata zonder documentinhoud.",
        )

    return _with_repo(settings.storage, op, require_writable=False)


@router.get("/research/sources")
def list_research_sources(
    asset_symbol: str | None = None,
    active_only: bool = False,
) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        if asset_symbol:
            records = repo.list_research_sources_for_asset(asset_symbol)
        elif active_only:
            records = repo.list_active_research_sources()
        else:
            records = repo.list_active_research_sources()
        return {
            "status_nl": "OK",
            "message_nl": "Onderzoeksbronnen opgehaald.",
            "help_nl": "Lijst bevat alleen metadatarecords.",
            "records": [asdict(r) for r in records],
        }

    return _with_repo(settings.storage, op, require_writable=False)


@router.post("/research/sources/{library_source_id}/uploaded-file-metadata")
def create_uploaded_file_metadata(
    library_source_id: str,
    payload: ResearchUploadedFileMetadataInput,
) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        record = ResearchUploadedFileMetadataRecord(
            library_source_id=_require_id(library_source_id, "library_source_id"),
            uploaded_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        saved = repo.save_uploaded_file_metadata(record)
        return _ok(
            (
                "Bestandsmetadata opgeslagen. Het bestand zelf wordt in deze stap "
                "niet geüpload of gelezen."
            ),
            asdict(saved),
            "Geen upload of parsing in deze endpoint.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.post("/research/sources/{library_source_id}/upload-file")
def upload_research_source_file(
    library_source_id: str,
    file: Annotated[UploadFile, File(...)],
    title: str | None = Form(default=None),
    asset_symbol: str | None = Form(default=None),
    asset_name: str | None = Form(default=None),
    document_type: str | None = Form(default=None),
    source_kind: str | None = Form(default=None),
    source_type: str | None = Form(default=None),
    explanation_nl: str | None = Form(default=None),
) -> dict[str, object]:
    if not settings.research_upload.enabled:
        raise HTTPException(status_code=503, detail="Bestand uploaden staat uit.")

    source_id = _require_id(library_source_id, "library_source_id")

    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        now = datetime.now(UTC)
        original_name, stored_name, file_size, hash_sha256, storage_uri = _archive_uploaded_file(
            upload=file,
            library_source_id=source_id,
            upload_settings=settings.research_upload,
        )
        source_record = ResearchSourceRecord(
            library_source_id=source_id,
            source_kind=source_kind or "user_uploaded_document",
            status="active",
            classification_status="pending",
            extraction_status="pending",
            analysis_status="pending",
            asset_symbol=asset_symbol,
            asset_name=asset_name,
            title=title or original_name,
            document_type=document_type or _default_document_type(original_name),
            source_type=source_type or "user_uploaded",
            source_credibility_level=None,
            prompt_injection_risk_level=None,
            content_hash_sha256=hash_sha256,
            archive_storage_uri=storage_uri,
            raw_source_available=True,
            created_at=now,
            updated_at=now,
            archived_at=None,
            schema_version="v1",
            explanation_nl=(
                explanation_nl
                or "Door gebruiker geüpload bestand voor later onderzoek."
            ),
        )
        uploaded_record = ResearchUploadedFileMetadataRecord(
            library_source_id=source_id,
            original_file_name=original_name,
            stored_file_name=stored_name,
            content_type=file.content_type,
            file_size_bytes=file_size,
            file_hash_sha256=hash_sha256,
            detected_language=None,
            page_count=None,
            uploaded_at=now,
            uploaded_by_user=True,
            explanation_nl="Bestand veilig gearchiveerd zonder parsing of analyse.",
        )
        processing_record = ResearchSourceProcessingStatusRecord(
            processing_id=f"upload-{source_id}-{int(now.timestamp())}",
            library_source_id=source_id,
            classification_status="pending",
            extraction_status="pending",
            analysis_status="pending",
            readiness_status="uploaded_metadata_only",
            can_be_used_in_research=False,
            can_be_used_in_suggestions=False,
            needs_user_review=True,
            blocks_suggestions=True,
            last_error_nl=None,
            checked_at=now,
            reason_nl=(
                "Bestand is geüpload, maar nog niet geclassificeerd, "
                "gelezen of geanalyseerd."
            ),
        )
        repo.save_research_source(source_record)
        repo.save_uploaded_file_metadata(uploaded_record)
        repo.save_processing_status(processing_record)
        return {
            "status_nl": "OK",
            "message_nl": (
                "Bestand veilig opgeslagen als onderzoeksbron. Het bestand is nog "
                "niet gelezen, geparseerd of geanalyseerd."
            ),
            "help_nl": (
                "Dit bestand is bewijs voor later onderzoek. "
                "Het maakt geen koop- of verkoopactie aan."
            ),
            "library_source_id": source_id,
            "original_file_name": original_name,
            "stored_file_name": stored_name,
            "file_size_bytes": file_size,
            "sha256": hash_sha256,
            "archive_storage_uri": storage_uri,
            "record": asdict(source_record),
        }

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/sources/{library_source_id}/uploaded-file-metadata")
def get_uploaded_file_metadata(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_uploaded_file_metadata(
            _require_id(library_source_id, "library_source_id")
        )
        if found is None:
            raise HTTPException(status_code=404, detail="Bestandsmetadata niet gevonden.")
        return _ok("Bestandsmetadata gevonden.", asdict(found), "Geen bestandinhoud opgeslagen.")

    return _with_repo(settings.storage, op, require_writable=False)


@router.post("/research/sources/{library_source_id}/url-metadata")
def create_url_metadata(
    library_source_id: str,
    payload: ResearchUrlMetadataInput,
) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        record = ResearchUrlMetadataRecord(
            library_source_id=_require_id(library_source_id, "library_source_id"),
            **payload.model_dump(),
        )
        saved = repo.save_url_metadata(record)
        return _ok(
            "URL-metadata opgeslagen. De URL wordt in deze stap niet opgehaald of geanalyseerd.",
            asdict(saved),
            "Alleen registratie, geen netwerkverkeer.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/sources/{library_source_id}/url-metadata")
def get_url_metadata(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_url_metadata(_require_id(library_source_id, "library_source_id"))
        if found is None:
            raise HTTPException(status_code=404, detail="URL-metadata niet gevonden.")
        return _ok(
            "URL-metadata gevonden.",
            asdict(found),
            "URL is niet opgehaald of geanalyseerd.",
        )

    return _with_repo(settings.storage, op, require_writable=False)


@router.post("/research/sources/{library_source_id}/user-note")
def create_user_note(
    library_source_id: str,
    payload: ResearchUserNoteInput,
) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        now = datetime.now(UTC)
        record = ResearchUserNoteRecord(
            library_source_id=_require_id(library_source_id, "library_source_id"),
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )
        saved = repo.save_user_note(record)
        return _ok(
            (
                "Gebruikersnotitie opgeslagen als onderzoeksbron. Dit is bewijs, "
                "geen handelsinstructie."
            ),
            asdict(saved),
            "Geen suggestie of order wordt gestart.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/sources/{library_source_id}/user-note")
def get_user_note(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_user_note(_require_id(library_source_id, "library_source_id"))
        if found is None:
            raise HTTPException(status_code=404, detail="Notitie niet gevonden.")
        return _ok(
            "Gebruikersnotitie gevonden.",
            asdict(found),
            "Notitie blijft bewijs, geen instructie.",
        )

    return _with_repo(settings.storage, op, require_writable=False)


@router.post("/research/document-sets")
def create_document_set(payload: ResearchDocumentSetInput) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        record = ResearchDocumentSetRecord(
            created_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        saved = repo.save_document_set(record)
        return _ok(
            "Documentenset opgeslagen. Vergelijking of analyse gebeurt later.",
            asdict(saved),
            "Alleen metadata-koppeling.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/document-sets/{document_set_id}")
def get_document_set(document_set_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_document_set(_require_id(document_set_id, "document_set_id"))
        if found is None:
            raise HTTPException(status_code=404, detail="Documentenset niet gevonden.")
        return _ok("Documentenset gevonden.", asdict(found), "Geen analyse uitgevoerd.")

    return _with_repo(settings.storage, op, require_writable=False)


@router.post("/research/document-sets/{document_set_id}/members")
def add_document_set_member(
    document_set_id: str,
    payload: ResearchDocumentSetMemberInput,
) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        record = ResearchDocumentSetMemberRecord(
            document_set_id=_require_id(document_set_id, "document_set_id"),
            created_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        saved = repo.save_document_set_member(record)
        return _ok(
            "Documentset-lid opgeslagen.",
            asdict(saved),
            "Alleen bronkoppeling, geen parsing.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/document-sets/{document_set_id}/members")
def list_document_set_members(document_set_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        records = repo.list_document_set_members(_require_id(document_set_id, "document_set_id"))
        return {
            "status_nl": "OK",
            "message_nl": "Documentset-leden opgehaald.",
            "help_nl": "Alleen metadatarecords.",
            "records": [asdict(x) for x in records],
        }

    return _with_repo(settings.storage, op, require_writable=False)


@router.post("/research/sources/{library_source_id}/classifications")
def create_classification(
    library_source_id: str,
    payload: ResearchDocumentClassificationInput,
) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        record = ResearchDocumentClassificationRecord(
            library_source_id=_require_id(library_source_id, "library_source_id"),
            classified_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        saved = repo.save_document_classification(record)
        return _ok(
            (
                "Classificatie opgeslagen als record. Er is geen automatische "
                "classificatie uitgevoerd."
            ),
            asdict(saved),
            "Geen AI-analyse uitgevoerd.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/sources/{library_source_id}/classifications/latest")
def get_latest_classification(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_latest_classification(
            _require_id(library_source_id, "library_source_id")
        )
        if found is None:
            raise HTTPException(status_code=404, detail="Classificatie niet gevonden.")
        return _ok(
            "Laatste classificatie gevonden.",
            asdict(found),
            "Record-only; geen automatische analyse.",
        )

    return _with_repo(settings.storage, op, require_writable=False)


@router.post("/research/sources/{library_source_id}/asset-links")
def create_asset_link(
    library_source_id: str,
    payload: ResearchSourceAssetLinkInput,
) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        record = ResearchSourceAssetLinkRecord(
            library_source_id=_require_id(library_source_id, "library_source_id"),
            created_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        saved = repo.save_source_asset_link(record)
        return _ok(
            (
                "Koppeling opgeslagen. Een nieuw gevonden asset wordt nog niet "
                "automatisch aan de volglijst toegevoegd."
            ),
            asdict(saved),
            "Geen watchlist/suggestie/IBKR-actie gestart.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/sources/{library_source_id}/asset-links")
def list_asset_links_for_source(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        records = repo.list_asset_links_for_source(
            _require_id(library_source_id, "library_source_id")
        )
        return {
            "status_nl": "OK",
            "message_nl": "Koppelingen opgehaald.",
            "help_nl": "Audit-link records zonder acties.",
            "records": [asdict(x) for x in records],
        }

    return _with_repo(settings.storage, op, require_writable=False)


@router.get("/research/asset-links/unconfirmed-detected")
def list_unconfirmed_asset_links() -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        records = repo.list_unconfirmed_detected_asset_links()
        return {
            "status_nl": "OK",
            "message_nl": "Niet-bevestigde nieuw-asset koppelingen opgehaald.",
            "help_nl": "Nog geen automatische volglijst-aanpassing.",
            "records": [asdict(x) for x in records],
        }

    return _with_repo(settings.storage, op, require_writable=False)


@router.post("/research/sources/{library_source_id}/processing-status")
def create_processing_status(
    library_source_id: str,
    payload: ResearchProcessingStatusInput,
) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        record = ResearchSourceProcessingStatusRecord(
            library_source_id=_require_id(library_source_id, "library_source_id"),
            checked_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        saved = repo.save_processing_status(record)
        return _ok(
            "Verwerkingsstatus opgeslagen. Er is geen analyse gestart.",
            asdict(saved),
            "Slaat alleen status op.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/sources/{library_source_id}/processing-status/latest")
def get_latest_processing_status(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_latest_processing_status(
            _require_id(library_source_id, "library_source_id")
        )
        if found is None:
            raise HTTPException(status_code=404, detail="Verwerkingsstatus niet gevonden.")
        return _ok(
            "Laatste verwerkingsstatus gevonden.",
            asdict(found),
            "Geen achtergrondverwerking gestart.",
        )

    return _with_repo(settings.storage, op, require_writable=False)




@router.post("/research/sources/{library_source_id}/credibility-assessment")
def create_source_credibility_assessment(
    library_source_id: str,
    payload: ResearchSourceCredibilityAssessmentInput,
) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        now = datetime.now(UTC)
        record = ResearchSourceCredibilityAssessmentRecord(
            library_source_id=_require_id(library_source_id, "library_source_id"),
            assessment_id=payload.assessment_id,
            credibility_status=payload.credibility_status,
            credibility_level=payload.credibility_level,
            source_category=payload.source_category,
            assessed_at=payload.assessed_at or now,
            checked_at=now,
            confidence_level=payload.confidence_level,
            credibility_signals_json=tuple(payload.credibility_signals),
            limitation_notes_nl=payload.limitation_notes_nl,
            safe_to_use_as_evidence=payload.safe_to_use_as_evidence,
            safe_to_use_for_suggestions=False,
            blocks_suggestions=True,
            explanation_nl=payload.explanation_nl,
        )
        saved = repo.save_source_credibility_assessment(record)
        return _ok(
            "Bron-credibilitystatus opgeslagen.",
            {**asdict(saved), "credibility_signals": list(saved.credibility_signals_json or ())},
            "Deze status is alleen audit-info; suggesties blijven geblokkeerd.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/sources/{library_source_id}/credibility-assessment/latest")
def get_latest_source_credibility_assessment(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_latest_source_credibility_assessment(_require_id(library_source_id, "library_source_id"))
        if found is None:
            return _ok(
                "Nog geen bron-credibilitybeoordeling gevonden.",
                {
                    "library_source_id": library_source_id,
                    "credibility_status": "not_assessed",
                    "credibility_level": "unknown",
                    "source_category": "unknown",
                    "confidence_level": "unknown",
                    "credibility_signals": [],
                    "limitation_notes_nl": "Nog niet beoordeeld.",
                    "safe_to_use_as_evidence": False,
                    "safe_to_use_for_suggestions": False,
                    "blocks_suggestions": True,
                    "checked_at": datetime.now(UTC).isoformat(),
                    "explanation_nl": "Bron is nog niet beoordeeld en blijft geblokkeerd voor suggesties.",
                },
                "Beoordeling is verplicht, maar zelfs daarna blijven suggesties in deze fase geblokkeerd.",
            )
        return _ok(
            "Laatste bron-credibilitybeoordeling gevonden.",
            {**asdict(found), "credibility_signals": list(found.credibility_signals_json or ())},
            "Zelfs hoge credibility ontgrendelt geen suggesties in versie 1 foundation.",
        )

    return _with_repo(settings.storage, op, require_writable=False)


@router.post("/research/sources/{library_source_id}/prompt-injection-scan")
def create_prompt_injection_scan_status(
    library_source_id: str,
    payload: ResearchPromptInjectionScanInput,
) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        now = datetime.now(UTC)
        record = ResearchSourcePromptInjectionScanRecord(
            library_source_id=_require_id(library_source_id, "library_source_id"),
            scan_id=payload.scan_id,
            scan_status=payload.scan_status,
            risk_level=payload.risk_level,
            detected_signals_json=tuple(payload.detected_signals),
            safe_to_use_as_evidence=payload.safe_to_use_as_evidence,
            safe_to_use_as_instruction=payload.safe_to_use_as_instruction,
            blocks_suggestions=True if payload.blocks_suggestions is False else payload.blocks_suggestions,
            scanned_at=payload.scanned_at or now,
            checked_at=now,
            explanation_nl=payload.explanation_nl,
        )
        saved = repo.save_prompt_injection_scan(record)
        return _ok(
            "Prompt-injection scanstatus opgeslagen.",
            {**asdict(saved), "detected_signals": list(saved.detected_signals_json or ())},
            "Zelfs bij lage risico blijft suggestie-gebruik geblokkeerd in versie 1.",
        )

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/sources/{library_source_id}/prompt-injection-scan/latest")
def get_latest_prompt_injection_scan(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        found = repo.get_latest_prompt_injection_scan(_require_id(library_source_id, "library_source_id"))
        if found is None:
            return _ok(
                "Nog geen prompt-injection scan gevonden.",
                {
                    "library_source_id": library_source_id,
                    "scan_status": "not_scanned",
                    "risk_level": "unknown",
                    "detected_signals": [],
                    "safe_to_use_as_evidence": False,
                    "safe_to_use_as_instruction": False,
                    "blocks_suggestions": True,
                    "checked_at": datetime.now(UTC).isoformat(),
                    "explanation_nl": "Bron is nog niet gescand en blijft geblokkeerd voor suggesties.",
                },
                "Eerst alle veiligheidscontroles afronden voordat suggesties ooit worden vrijgegeven.",
            )
        return _ok(
            "Laatste prompt-injection scanstatus gevonden.",
            {**asdict(found), "detected_signals": list(found.detected_signals_json or ())},
            "Scanresultaat is audit-info; suggesties blijven geblokkeerd.",
        )

    return _with_repo(settings.storage, op, require_writable=False)


@router.post("/research/sources/{library_source_id}/classify-deterministic")
def classify_research_source_deterministic(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        source_id = _require_id(library_source_id, "library_source_id")
        source = repo.get_research_source(source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Onderzoeksbron niet gevonden.")
        metadata = repo.get_uploaded_file_metadata(source_id)
        extracted = repo.get_latest_extracted_text_for_source(source_id)

        kind_value = source.source_kind.strip().lower()
        try:
            source_kind = ResearchLibrarySourceKind(kind_value)
        except ValueError:
            source_kind = ResearchLibrarySourceKind.UNKNOWN

        extracted_preview = extracted.preview_text_nl if extracted else None
        now = datetime.now(UTC)
        result = classify_document_deterministically(
            library_source_id=source_id,
            source_kind=source_kind,
            title=source.title,
            original_file_name=metadata.original_file_name if metadata else None,
            extracted_text=extracted_preview,
            classified_at=now,
        )
        classification_id = f"det-{source_id}-{int(now.timestamp())}"
        record = ResearchDocumentClassificationRecord(
            classification_id=classification_id,
            library_source_id=source_id,
            document_type=result.category.value,
            source_type=source.source_type,
            confidence=result.confidence.value,
            detected_asset_symbol=source.asset_symbol,
            detected_asset_name=source.asset_name,
            detected_fiscal_year=None,
            detected_reporting_period=None,
            detected_language=metadata.detected_language if metadata else None,
            needs_user_review=result.needs_user_review,
            reason_nl=result.reason_nl,
            classified_at=now,
            schema_version="v1",
        )
        status = ResearchSourceProcessingStatusRecord(
            processing_id=f"classification-{source_id}-{int(now.timestamp())}",
            library_source_id=source_id,
            classification_status="deterministic_classified",
            extraction_status="extracted" if extracted else "pending",
            analysis_status="not_started",
            readiness_status="classified_metadata_only",
            can_be_used_in_research=False,
            can_be_used_in_suggestions=False,
            needs_user_review=True,
            blocks_suggestions=True,
            last_error_nl=None,
            checked_at=now,
            reason_nl=result.reason_nl,
        )
        repo.save_document_classification(record)
        repo.save_processing_status(status)
        return {
            "status_nl": "OK",
            "message_nl": "Deterministische classificatie opgeslagen.",
            "help_nl": "Alleen veilige metadata-classificatie. Geen suggestieflow.",
            "record": asdict(record),
            "classification_result": result.model_dump(),
        }

    return _with_repo(settings.storage, op, require_writable=True)


@router.post("/research/sources/{library_source_id}/extract-text")
def extract_research_source_text(library_source_id: str) -> dict[str, object]:
    if not settings.research_extraction.enabled:
        raise HTTPException(status_code=503, detail="Tekstextractie staat uit.")

    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        source_id = _require_id(library_source_id, "library_source_id")
        source = repo.get_research_source(source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Onderzoeksbron niet gevonden.")
        metadata = repo.get_uploaded_file_metadata(source_id)
        if metadata is None:
            raise HTTPException(status_code=404, detail="Bestandsmetadata niet gevonden.")
        if source.archive_storage_uri is None:
            raise HTTPException(status_code=404, detail="Bronbestand ontbreekt in het archief.")
        extracted = _extract_plain_research_text(
            source_archive_uri=source.archive_storage_uri,
            original_filename=metadata.original_file_name,
            library_source_id=source_id,
            upload_settings=settings.research_upload,
            extraction_settings=settings.research_extraction,
        )
        now = datetime.now(UTC)
        extracted_id = f"ext-{source_id}-{int(now.timestamp())}"
        record = ResearchExtractedTextRecord(
            extracted_text_id=extracted_id,
            library_source_id=source_id,
            source_file_hash_sha256=metadata.file_hash_sha256,
            extraction_status="extracted",
            extraction_method="deterministic_plain_text_v1",
            detected_content_type=metadata.content_type,
            detected_language=None,
            character_count=extracted.character_count,
            line_count=extracted.line_count,
            text_hash_sha256=extracted.text_hash_sha256,
            extracted_text_storage_uri=extracted.extracted_text_storage_uri,
            preview_text_nl=extracted.preview_text_nl,
            can_be_used_in_research=False,
            can_be_used_in_suggestions=False,
            needs_user_review=True,
            blocks_suggestions=True,
            created_at=now,
            extracted_at=now,
            schema_version="v1",
            reason_nl="Deterministische tekstextractie uitgevoerd; nog geen analyse.",
        )
        status = ResearchSourceProcessingStatusRecord(
            processing_id=f"extract-{source_id}-{int(now.timestamp())}",
            library_source_id=source_id,
            classification_status="pending",
            extraction_status="extracted",
            analysis_status="not_started",
            readiness_status="extracted_text_metadata_only",
            can_be_used_in_research=False,
            can_be_used_in_suggestions=False,
            needs_user_review=True,
            blocks_suggestions=True,
            last_error_nl=None,
            checked_at=now,
            reason_nl=(
                "Tekst is geëxtraheerd, maar nog niet gecontroleerd op bronkwaliteit, "
                "actualiteit of kwaadaardige instructies. Daarom mag ze nog geen "
                "invloed hebben op suggesties."
            ),
        )
        repo.save_extracted_text(record)
        repo.save_processing_status(status)
        return {
            "status_nl": "OK",
            "message_nl": (
                "Tekst veilig geëxtraheerd en opgeslagen als onderzoeksmetadata. "
                "De inhoud is nog niet geanalyseerd of gebruikt voor suggesties."
            ),
            "help_nl": (
                "Deze tekst is bewijs voor later onderzoek. Ze maakt geen koop- of "
                "verkoopactie aan en blijft geblokkeerd voor suggesties tot latere "
                "controles klaar zijn."
            ),
            "library_source_id": source_id,
            "extracted_text_id": extracted_id,
            "extraction_status": "extracted",
            "character_count": extracted.character_count,
            "line_count": extracted.line_count,
            "text_hash_sha256": extracted.text_hash_sha256,
            "extracted_text_storage_uri": extracted.extracted_text_storage_uri,
            "preview_text_nl": extracted.preview_text_nl,
            "blocks_suggestions": True,
            "can_be_used_in_suggestions": False,
            "record": asdict(record),
        }

    return _with_repo(settings.storage, op, require_writable=True)


@router.post("/research/sources/{library_source_id}/evidence-items")
def create_source_evidence_item(library_source_id: str, payload: ResearchSourceEvidenceItemInput) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        source_id = _require_id(library_source_id, "library_source_id")
        if repo.get_research_source(source_id) is None:
            raise HTTPException(status_code=404, detail="Onderzoeksbron niet gevonden.")
        now = datetime.now(UTC)
        record = ResearchSourceEvidenceItemRecord(
            evidence_item_id=payload.evidence_item_id,
            library_source_id=source_id,
            evidence_type=payload.evidence_type,
            evidence_status=payload.evidence_status,
            extracted_from_kind=payload.extracted_from_kind,
            source_reference_text=payload.source_reference_text,
            normalized_evidence_text=payload.normalized_evidence_text,
            evidence_summary_nl=payload.evidence_summary_nl,
            asset_symbol=payload.asset_symbol,
            reporting_period=payload.reporting_period,
            fiscal_year=payload.fiscal_year,
            confidence_level=payload.confidence_level,
            extraction_method=payload.extraction_method,
            source_text_hash_sha256=payload.source_text_hash_sha256,
            extraction_run_id=payload.extraction_run_id,
            created_at=now,
            extracted_at=payload.extracted_at or now,
            safe_to_use_as_evidence=payload.safe_to_use_as_evidence,
            safe_to_use_for_suggestions=False,
            blocks_suggestions=True,
            explanation_nl=payload.explanation_nl,
        )
        saved = repo.save_source_evidence_item(record)
        return _ok("Bewijsitem opgeslagen voor later onderzoek.", asdict(saved), "Bewijsitems ontgrendelen nog geen suggesties in versie 1.")

    return _with_repo(settings.storage, op, require_writable=True)


@router.get("/research/sources/{library_source_id}/evidence-items")
def list_source_evidence_items(library_source_id: str) -> dict[str, object]:
    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> dict[str, object]:
        source_id = _require_id(library_source_id, "library_source_id")
        if repo.get_research_source(source_id) is None:
            return {"status_nl": "OK", "message_nl": "Onderzoeksbron niet gevonden; bewijs blijft geblokkeerd.", "help_nl": "Er zijn geen bewijsitems en suggesties blijven geblokkeerd.", "records": []}
        records = repo.list_source_evidence_items(source_id)
        if not records:
            return {"status_nl": "OK", "message_nl": "Nog geen bewijsitems voor deze bron.", "help_nl": "Zonder bewijsitems blijft de bron geblokkeerd voor suggesties.", "records": []}
        return {"status_nl": "OK", "message_nl": "Bewijsitems opgehaald.", "help_nl": "Bewijsitems zijn alleen audit- en onderzoeksinformatie; suggesties blijven geblokkeerd.", "records": [asdict(x) for x in records]}

    return _with_repo(settings.storage, op, require_writable=False)
