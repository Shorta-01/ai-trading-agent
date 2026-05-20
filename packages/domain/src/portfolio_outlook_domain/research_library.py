from datetime import datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from .primitives import DomainBaseModel
from .research_suggestions import (
    PromptInjectionAssessment,
    PromptInjectionRiskLevel,
    ResearchDocumentType,
    ResearchSourceType,
    SourceCredibilityAssessment,
    SourceCredibilityLevel,
)


class ResearchLibrarySourceKind(StrEnum):
    UPLOADED_FILE = "uploaded_file"
    URL = "url"
    USER_NOTE = "user_note"
    MANUAL_REFERENCE = "manual_reference"
    UNKNOWN = "unknown"


class ResearchLibrarySourceStatus(StrEnum):
    DRAFT = "draft"
    ADDED = "added"
    STORED = "stored"
    AWAITING_CLASSIFICATION = "awaiting_classification"
    CLASSIFIED = "classified"
    EXTRACTION_PENDING = "extraction_pending"
    EXTRACTION_FAILED = "extraction_failed"
    EXTRACTED = "extracted"
    ANALYSIS_PENDING = "analysis_pending"
    ANALYZED = "analyzed"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    FAILED = "failed"


class ResearchLibraryClassificationStatus(StrEnum):
    NOT_CLASSIFIED = "not_classified"
    AUTO_CLASSIFIED = "auto_classified"
    USER_CLASSIFIED = "user_classified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class ResearchExtractionStatus(StrEnum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    EXTRACTED = "extracted"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_SUPPORTED = "not_supported"


class ResearchAnalysisStatus(StrEnum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    VALIDATION_FAILED = "validation_failed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ResearchLibrarySource(DomainBaseModel):
    library_source_id: str
    source_kind: ResearchLibrarySourceKind
    status: ResearchLibrarySourceStatus
    classification_status: ResearchLibraryClassificationStatus
    extraction_status: ResearchExtractionStatus
    analysis_status: ResearchAnalysisStatus
    asset_symbol: str | None = None
    asset_name: str | None = None
    title: str
    user_description_nl: str | None = None
    document_type: ResearchDocumentType
    source_type: ResearchSourceType
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    explanation_nl: str

    @field_validator("library_source_id", "title")
    @classmethod
    def _required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_dates(self) -> "ResearchLibrarySource":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        if self.archived_at is not None and self.archived_at < self.created_at:
            raise ValueError("archived_at must not be earlier than created_at")
        return self


class UploadedResearchFileMetadata(DomainBaseModel):
    library_source_id: str
    original_file_name: str
    stored_file_name: str | None = None
    content_type: str | None = None
    file_size_bytes: int | None = None
    file_hash_sha256: str | None = None
    detected_language: str | None = None
    page_count: int | None = None
    uploaded_at: datetime
    uploaded_by_user: bool
    explanation_nl: str

    @field_validator("original_file_name")
    @classmethod
    def _filename_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("original_file_name must be non-empty")
        return value

    @field_validator("file_hash_sha256")
    @classmethod
    def _hash_non_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("file_hash_sha256 must be non-empty when present")
        return value

    @field_validator("file_size_bytes", "page_count")
    @classmethod
    def _positive_optional_int(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("value must be positive when present")
        return value


class ResearchUrlMetadata(DomainBaseModel):
    library_source_id: str
    url: str
    normalized_url: str | None = None
    domain: str | None = None
    fetched_at: datetime | None = None
    snapshot_hash_sha256: str | None = None
    http_status_code: int | None = None
    content_type: str | None = None
    user_supplied: bool
    explanation_nl: str

    @field_validator("url")
    @classmethod
    def _url_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("url must be non-empty")
        return value

    @field_validator("http_status_code")
    @classmethod
    def _valid_http_status(cls, value: int | None) -> int | None:
        if value is not None and not (100 <= value <= 599):
            raise ValueError("http_status_code must be between 100 and 599")
        return value


class UserResearchNote(DomainBaseModel):
    library_source_id: str
    asset_symbol: str | None = None
    title: str
    note_nl: str
    created_at: datetime
    updated_at: datetime
    thesis_relevance_nl: str | None = None
    user_confidence_nl: str | None = None
    explanation_nl: str

    @field_validator("title", "note_nl")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must be non-empty")
        return value

    @model_validator(mode="after")
    def _note_dates(self) -> "UserResearchNote":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        return self


class ResearchDocumentSetType(StrEnum):
    ANNUAL_REPORTS = "annual_reports"
    QUARTERLY_REPORTS = "quarterly_reports"
    INVESTOR_PRESENTATIONS = "investor_presentations"
    ETF_FACTSHEETS = "etf_factsheets"
    MIXED_DOCUMENTS = "mixed_documents"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class ResearchDocumentSet(DomainBaseModel):
    document_set_id: str
    asset_symbol: str
    title: str
    set_type: ResearchDocumentSetType
    library_source_ids: tuple[str, ...]
    fiscal_years: tuple[int, ...] = ()
    reporting_periods: tuple[str, ...] = ()
    created_at: datetime
    explanation_nl: str

    @field_validator("document_set_id", "asset_symbol", "title")
    @classmethod
    def _required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_set(self) -> "ResearchDocumentSet":
        if not self.library_source_ids:
            raise ValueError("library_source_ids must contain at least one id")
        if len(set(self.fiscal_years)) != len(self.fiscal_years):
            raise ValueError("fiscal_years must not contain duplicates")
        for year in self.fiscal_years:
            if year < 1900 or year > 2200:
                raise ValueError("fiscal_year out of supported range")
        return self


class DocumentClassificationConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ResearchDocumentClassification(DomainBaseModel):
    library_source_id: str
    document_type: ResearchDocumentType
    source_type: ResearchSourceType
    confidence: DocumentClassificationConfidence
    detected_asset_symbol: str | None = None
    detected_asset_name: str | None = None
    detected_fiscal_year: int | None = None
    detected_reporting_period: str | None = None
    detected_language: str | None = None
    needs_user_review: bool
    reason_nl: str
    classified_at: datetime

    @field_validator("reason_nl")
    @classmethod
    def _reason_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_nl must be non-empty")
        return value

    @model_validator(mode="after")
    def _low_confidence_needs_review(self) -> "ResearchDocumentClassification":
        if self.confidence in {
            DocumentClassificationConfidence.LOW,
            DocumentClassificationConfidence.UNKNOWN,
        } and not self.needs_user_review:
            raise ValueError("low/unknown confidence must require user review")
        return self


class DeterministicDocumentCategory(StrEnum):
    ANNUAL_REPORT = "annual_report"
    QUARTERLY_REPORT = "quarterly_report"
    INVESTOR_PRESENTATION = "investor_presentation"
    ETF_FACTSHEET = "etf_factsheet"
    NEWS_ARTICLE = "news_article"
    BROKER_REPORT = "broker_report"
    USER_NOTE = "user_note"
    MARKET_DATA_EXPORT = "market_data_export"
    UNKNOWN = "unknown"


class DeterministicClassificationMethod(StrEnum):
    METADATA_ONLY = "metadata_only"
    METADATA_AND_EXTRACTED_TEXT = "metadata_and_extracted_text"


class DeterministicDocumentClassificationResult(DomainBaseModel):
    library_source_id: str
    category: DeterministicDocumentCategory
    method: DeterministicClassificationMethod
    matched_signals: tuple[str, ...]
    confidence: DocumentClassificationConfidence
    can_be_used_in_research: bool
    can_be_used_in_suggestions: bool
    blocks_suggestions: bool
    needs_user_review: bool
    reason_nl: str
    classified_at: datetime


def classify_document_deterministically(
    *,
    library_source_id: str,
    source_kind: ResearchLibrarySourceKind,
    title: str,
    original_file_name: str | None = None,
    extracted_text: str | None = None,
    classified_at: datetime,
) -> DeterministicDocumentClassificationResult:
    metadata = f"{title} {original_file_name or ''}".lower()
    text = (extracted_text or "").lower()
    signals: list[str] = []

    def has(*words: str) -> bool:
        return any(word in metadata or (text and word in text) for word in words)

    category = DeterministicDocumentCategory.UNKNOWN
    confidence = DocumentClassificationConfidence.UNKNOWN

    if source_kind == ResearchLibrarySourceKind.USER_NOTE:
        category = DeterministicDocumentCategory.USER_NOTE
        signals.append("source_kind:user_note")
        confidence = DocumentClassificationConfidence.HIGH
    elif has(
        "annual report",
        "annual-report",
        "annual_report",
        "annual rep",
        "jaarverslag",
        "form 10-k",
    ):
        category = DeterministicDocumentCategory.ANNUAL_REPORT
        signals.append("keyword:annual_report")
        confidence = DocumentClassificationConfidence.MEDIUM
    elif has("quarterly report", "kwartaal", "form 10-q"):
        category = DeterministicDocumentCategory.QUARTERLY_REPORT
        signals.append("keyword:quarterly_report")
        confidence = DocumentClassificationConfidence.MEDIUM
    elif has("investor presentation", "investor deck", "presentation"):
        category = DeterministicDocumentCategory.INVESTOR_PRESENTATION
        signals.append("keyword:investor_presentation")
        confidence = DocumentClassificationConfidence.MEDIUM
    elif has("factsheet", "fact sheet", "kiid", "etf"):
        category = DeterministicDocumentCategory.ETF_FACTSHEET
        signals.append("keyword:etf_factsheet")
        confidence = DocumentClassificationConfidence.MEDIUM
    elif has("reuters", "bloomberg", "news", "nieuws"):
        category = DeterministicDocumentCategory.NEWS_ARTICLE
        signals.append("keyword:news_article")
        confidence = DocumentClassificationConfidence.LOW
    elif has("broker report", "analyst report", "analistenrapport"):
        category = DeterministicDocumentCategory.BROKER_REPORT
        signals.append("keyword:broker_report")
        confidence = DocumentClassificationConfidence.LOW
    elif has("open,high,low,close", "timestamp", "volume", "csv export"):
        category = DeterministicDocumentCategory.MARKET_DATA_EXPORT
        signals.append("keyword:market_data_export")
        confidence = DocumentClassificationConfidence.MEDIUM

    method = (
        DeterministicClassificationMethod.METADATA_AND_EXTRACTED_TEXT
        if extracted_text
        else DeterministicClassificationMethod.METADATA_ONLY
    )
    if not signals:
        signals.append("fallback:unknown")

    return DeterministicDocumentClassificationResult(
        library_source_id=library_source_id,
        category=category,
        method=method,
        matched_signals=tuple(signals),
        confidence=confidence,
        can_be_used_in_research=False,
        can_be_used_in_suggestions=False,
        blocks_suggestions=True,
        needs_user_review=True,
        reason_nl=(
            "Deterministische classificatie is alleen metadata voor audit. "
            "Deze bron blijft geblokkeerd voor suggesties tot latere validatiegates."
        ),
        classified_at=classified_at,
    )


class ResearchLibraryReadinessStatus(StrEnum):
    READY = "ready"
    NEEDS_USER_INPUT = "needs_user_input"
    WAITING_FOR_EXTRACTION = "waiting_for_extraction"
    WAITING_FOR_ANALYSIS = "waiting_for_analysis"
    BLOCKED = "blocked"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ResearchLibrarySourceReadiness(DomainBaseModel):
    library_source_id: str
    status: ResearchLibraryReadinessStatus
    can_be_used_in_research: bool
    can_be_used_in_suggestions: bool
    needs_user_review: bool
    blocks_suggestions: bool
    reason_nl: str
    checked_at: datetime


def evaluate_research_library_source_readiness(
    *,
    library_source_id: str,
    source_status: ResearchLibrarySourceStatus,
    classification_status: ResearchLibraryClassificationStatus,
    extraction_status: ResearchExtractionStatus,
    analysis_status: ResearchAnalysisStatus,
    prompt_injection_assessment: PromptInjectionAssessment | None = None,
    source_credibility_assessment: SourceCredibilityAssessment | None = None,
    checked_at: datetime,
) -> ResearchLibrarySourceReadiness:
    if source_status in {
        ResearchLibrarySourceStatus.ARCHIVED,
        ResearchLibrarySourceStatus.REJECTED,
        ResearchLibrarySourceStatus.FAILED,
    }:
        return ResearchLibrarySourceReadiness(
            library_source_id=library_source_id,
            status=ResearchLibraryReadinessStatus.FAILED,
            can_be_used_in_research=False,
            can_be_used_in_suggestions=False,
            needs_user_review=False,
            blocks_suggestions=True,
            reason_nl="Bron is niet bruikbaar door status (archief/afgewezen/mislukt).",
            checked_at=checked_at,
        )
    if prompt_injection_assessment and prompt_injection_assessment.risk_level in {
        PromptInjectionRiskLevel.HIGH,
        PromptInjectionRiskLevel.BLOCKED,
    }:
        return ResearchLibrarySourceReadiness(
            library_source_id=library_source_id,
            status=ResearchLibraryReadinessStatus.BLOCKED,
            can_be_used_in_research=False,
            can_be_used_in_suggestions=False,
            needs_user_review=True,
            blocks_suggestions=True,
            reason_nl="Prompt-injection risico is te hoog.",
            checked_at=checked_at,
        )
    if extraction_status in {
        ResearchExtractionStatus.PENDING,
        ResearchExtractionStatus.NOT_STARTED,
    }:
        return ResearchLibrarySourceReadiness(
            library_source_id=library_source_id,
            status=ResearchLibraryReadinessStatus.WAITING_FOR_EXTRACTION,
            can_be_used_in_research=False,
            can_be_used_in_suggestions=False,
            needs_user_review=False,
            blocks_suggestions=False,
            reason_nl="Extractie is nog niet klaar.",
            checked_at=checked_at,
        )
    needs_review = classification_status in {
        ResearchLibraryClassificationStatus.NOT_CLASSIFIED,
        ResearchLibraryClassificationStatus.NEEDS_REVIEW,
    }
    if analysis_status in {ResearchAnalysisStatus.PENDING, ResearchAnalysisStatus.RUNNING}:
        return ResearchLibrarySourceReadiness(
            library_source_id=library_source_id,
            status=ResearchLibraryReadinessStatus.WAITING_FOR_ANALYSIS,
            can_be_used_in_research=True,
            can_be_used_in_suggestions=False,
            needs_user_review=needs_review,
            blocks_suggestions=False,
            reason_nl="Analyse is nog bezig.",
            checked_at=checked_at,
        )

    credibility_blocked = (
        source_credibility_assessment is not None
        and source_credibility_assessment.credibility_level == SourceCredibilityLevel.BLOCKED
    )
    return ResearchLibrarySourceReadiness(
        library_source_id=library_source_id,
        status=ResearchLibraryReadinessStatus.READY,
        can_be_used_in_research=not credibility_blocked,
        can_be_used_in_suggestions=not (needs_review or credibility_blocked),
        needs_user_review=needs_review,
        blocks_suggestions=needs_review or credibility_blocked,
        reason_nl="Bron kan gebruikt worden als bewijs, niet als instructie.",
        checked_at=checked_at,
    )


class ResearchLibraryHelpText(DomainBaseModel):
    key: str
    label_nl: str
    help_nl: str


def get_research_library_help_texts() -> tuple[ResearchLibraryHelpText, ...]:
    return (
        ResearchLibraryHelpText(
            key="uploaded_file",
            label_nl="Bestand uploaden",
            help_nl="Voeg een document toe als bewijs, niet als instructie.",
        ),
        ResearchLibraryHelpText(
            key="url",
            label_nl="URL toevoegen",
            help_nl="Voeg een webbron toe als bewijs, niet als instructie.",
        ),
        ResearchLibraryHelpText(
            key="user_note",
            label_nl="Notitie toevoegen",
            help_nl="Jouw notitie telt als bewijs en wordt altijd gecontroleerd.",
        ),
        ResearchLibraryHelpText(
            key="asset_symbol",
            label_nl="Symbool",
            help_nl="Koppel de bron aan een ticker of fonds symbool.",
        ),
        ResearchLibraryHelpText(
            key="document_type",
            label_nl="Documenttype",
            help_nl="Geef aan wat voor document dit is, zoals jaarverslag.",
        ),
        ResearchLibraryHelpText(
            key="source_type",
            label_nl="Brontype",
            help_nl="Bronkwaliteit hangt af van het type en de herkomst.",
        ),
        ResearchLibraryHelpText(
            key="fiscal_year",
            label_nl="Boekjaar",
            help_nl="Gebruik het boekjaar om meerdere jaren te vergelijken.",
        ),
        ResearchLibraryHelpText(
            key="reporting_period",
            label_nl="Rapportageperiode",
            help_nl="Bijvoorbeeld Q1, H1 of volledig jaar.",
        ),
        ResearchLibraryHelpText(
            key="source_credibility",
            label_nl="Bronkwaliteit",
            help_nl="Gebruikersbronnen worden niet automatisch betrouwbaar.",
        ),
        ResearchLibraryHelpText(
            key="prompt_injection_check",
            label_nl="Prompt-injection controle",
            help_nl="Verdachte instructies blokkeren gebruik in suggesties.",
        ),
        ResearchLibraryHelpText(
            key="extraction_status",
            label_nl="Extractie status",
            help_nl="Laat zien of inhoud technisch is voorbereid voor analyse.",
        ),
        ResearchLibraryHelpText(
            key="analysis_status",
            label_nl="Analyse status",
            help_nl="Laat zien of de analyse klaar is voor gebruik.",
        ),
        ResearchLibraryHelpText(
            key="document_set",
            label_nl="Jaarverslagen vergelijken",
            help_nl="Groepeer meerdere documenten per aandeel of fonds.",
        ),
        ResearchLibraryHelpText(
            key="archive_source",
            label_nl="Bron archiveren",
            help_nl="Gearchiveerde bronnen tellen niet mee voor suggesties.",
        ),
    )
