from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain.research_library import (
    DeterministicDocumentCategory,
    DocumentClassificationConfidence,
    ResearchAnalysisStatus,
    ResearchDocumentClassification,
    ResearchDocumentSet,
    ResearchDocumentSetType,
    ResearchExtractionStatus,
    ResearchLibraryClassificationStatus,
    ResearchLibrarySource,
    ResearchLibrarySourceKind,
    ResearchLibrarySourceStatus,
    ResearchUrlMetadata,
    UploadedResearchFileMetadata,
    UserResearchNote,
    classify_document_deterministically,
    evaluate_research_library_source_readiness,
    get_research_library_help_texts,
)
from portfolio_outlook_domain.research_suggestions import (
    PromptInjectionAssessment,
    PromptInjectionRiskLevel,
    ResearchDocumentType,
    ResearchSourceType,
)

NOW = datetime(2026, 1, 2, tzinfo=UTC)


def test_research_library_source_requires_non_empty_id() -> None:
    with pytest.raises(ValidationError):
        _build_source(library_source_id="")


def test_research_library_source_requires_non_empty_title() -> None:
    with pytest.raises(ValidationError):
        _build_source(title="")


def test_source_updated_at_cannot_be_before_created_at() -> None:
    with pytest.raises(ValidationError):
        _build_source(updated_at=datetime(2025, 1, 1, tzinfo=UTC))


def test_uploaded_file_metadata_requires_non_empty_original_filename() -> None:
    with pytest.raises(ValidationError):
        UploadedResearchFileMetadata(
            library_source_id="src-1",
            original_file_name="",
            uploaded_at=NOW,
            uploaded_by_user=True,
            explanation_nl="Bestand metadata.",
        )


def test_uploaded_file_metadata_rejects_invalid_positive_values() -> None:
    with pytest.raises(ValidationError):
        UploadedResearchFileMetadata(
            library_source_id="src-1",
            original_file_name="q4.pdf",
            file_size_bytes=0,
            uploaded_at=NOW,
            uploaded_by_user=True,
            explanation_nl="Bestand metadata.",
        )
    with pytest.raises(ValidationError):
        UploadedResearchFileMetadata(
            library_source_id="src-1",
            original_file_name="q4.pdf",
            page_count=-1,
            uploaded_at=NOW,
            uploaded_by_user=True,
            explanation_nl="Bestand metadata.",
        )


def test_url_metadata_requires_non_empty_url() -> None:
    with pytest.raises(ValidationError):
        ResearchUrlMetadata(
            library_source_id="src-1",
            url="",
            user_supplied=True,
            explanation_nl="URL metadata.",
        )


def test_url_metadata_rejects_invalid_http_status() -> None:
    with pytest.raises(ValidationError):
        ResearchUrlMetadata(
            library_source_id="src-1",
            url="https://example.com",
            http_status_code=99,
            user_supplied=True,
            explanation_nl="URL metadata.",
        )


def test_user_note_requires_non_empty_title_and_note() -> None:
    with pytest.raises(ValidationError):
        UserResearchNote(
            library_source_id="src-1",
            title="",
            note_nl="nota",
            created_at=NOW,
            updated_at=NOW,
            explanation_nl="Notitie is bewijs, geen instructie.",
        )
    with pytest.raises(ValidationError):
        UserResearchNote(
            library_source_id="src-1",
            title="Titel",
            note_nl="",
            created_at=NOW,
            updated_at=NOW,
            explanation_nl="Notitie is bewijs, geen instructie.",
        )


def test_document_set_validations() -> None:
    with pytest.raises(ValidationError):
        _build_set(asset_symbol="")
    with pytest.raises(ValidationError):
        _build_set(library_source_ids=())
    with pytest.raises(ValidationError):
        _build_set(fiscal_years=(2024, 2024))


def test_classification_low_and_unknown_confidence_need_review() -> None:
    with pytest.raises(ValidationError):
        _build_classification(
            confidence=DocumentClassificationConfidence.LOW,
            needs_user_review=False,
        )
    with pytest.raises(ValidationError):
        _build_classification(
            confidence=DocumentClassificationConfidence.UNKNOWN,
            needs_user_review=False,
        )


def test_archived_rejected_failed_sources_not_usable_in_suggestions() -> None:
    for status in (
        ResearchLibrarySourceStatus.ARCHIVED,
        ResearchLibrarySourceStatus.REJECTED,
        ResearchLibrarySourceStatus.FAILED,
    ):
        readiness = evaluate_research_library_source_readiness(
            library_source_id="src-1",
            source_status=status,
            classification_status=ResearchLibraryClassificationStatus.AUTO_CLASSIFIED,
            extraction_status=ResearchExtractionStatus.EXTRACTED,
            analysis_status=ResearchAnalysisStatus.COMPLETED,
            checked_at=NOW,
        )
        assert readiness.can_be_used_in_suggestions is False


def test_prompt_injection_blocked_source_not_usable_in_suggestions() -> None:
    readiness = evaluate_research_library_source_readiness(
        library_source_id="src-1",
        source_status=ResearchLibrarySourceStatus.ANALYZED,
        classification_status=ResearchLibraryClassificationStatus.AUTO_CLASSIFIED,
        extraction_status=ResearchExtractionStatus.EXTRACTED,
        analysis_status=ResearchAnalysisStatus.COMPLETED,
        prompt_injection_assessment=PromptInjectionAssessment(
            source_id="src-1",
            risk_level=PromptInjectionRiskLevel.BLOCKED,
            signals=(),
            safe_to_use_as_evidence=False,
            safe_to_use_as_instruction=False,
            assessed_at=NOW,
            explanation_nl="Geblokkeerd.",
        ),
        checked_at=NOW,
    )
    assert readiness.can_be_used_in_suggestions is False


def test_user_uploaded_source_not_automatically_high_credibility() -> None:
    source = _build_source(source_type=ResearchSourceType.USER_UPLOADED_DOCUMENT)
    assert source.source_type == ResearchSourceType.USER_UPLOADED_DOCUMENT


def test_help_texts_exist_and_are_dutch_non_empty() -> None:
    texts = get_research_library_help_texts()
    assert len(texts) >= 14
    for text in texts:
        assert text.label_nl.strip()
        assert text.help_nl.strip()
    assert any("bewijs" in text.help_nl.lower() for text in texts)


def test_no_contract_stores_raw_file_bytes() -> None:
    assert "file_bytes" not in UploadedResearchFileMetadata.model_fields


def _build_source(**overrides: object) -> ResearchLibrarySource:
    payload = {
        "library_source_id": "src-1",
        "source_kind": ResearchLibrarySourceKind.UPLOADED_FILE,
        "status": ResearchLibrarySourceStatus.ADDED,
        "classification_status": ResearchLibraryClassificationStatus.NOT_CLASSIFIED,
        "extraction_status": ResearchExtractionStatus.NOT_STARTED,
        "analysis_status": ResearchAnalysisStatus.NOT_STARTED,
        "title": "Q4 Jaarverslag",
        "document_type": ResearchDocumentType.ANNUAL_REPORT,
        "source_type": ResearchSourceType.USER_UPLOADED_DOCUMENT,
        "created_at": NOW,
        "updated_at": NOW,
        "explanation_nl": "Bron is bewijs, geen instructie.",
    }
    payload.update(overrides)
    return ResearchLibrarySource(**payload)


def _build_set(**overrides: object) -> ResearchDocumentSet:
    payload = {
        "document_set_id": "set-1",
        "asset_symbol": "ASML",
        "title": "Laatste jaarverslagen",
        "set_type": ResearchDocumentSetType.ANNUAL_REPORTS,
        "library_source_ids": ("src-1",),
        "fiscal_years": (2024,),
        "created_at": NOW,
        "explanation_nl": "Voor vergelijking over meerdere jaren.",
    }
    payload.update(overrides)
    return ResearchDocumentSet(**payload)


def _build_classification(**overrides: object) -> ResearchDocumentClassification:
    payload = {
        "library_source_id": "src-1",
        "document_type": ResearchDocumentType.ANNUAL_REPORT,
        "source_type": ResearchSourceType.USER_UPLOADED_DOCUMENT,
        "confidence": DocumentClassificationConfidence.MEDIUM,
        "needs_user_review": False,
        "reason_nl": "Classificatie voorlopig.",
        "classified_at": NOW,
    }
    payload.update(overrides)
    return ResearchDocumentClassification(**payload)


def test_deterministic_classification_for_user_note_is_blocked_for_suggestions() -> None:
    result = classify_document_deterministically(
        library_source_id="src-note",
        source_kind=ResearchLibrarySourceKind.USER_NOTE,
        title="Eigen notitie",
        original_file_name=None,
        extracted_text="",
        classified_at=NOW,
    )
    assert result.category == DeterministicDocumentCategory.USER_NOTE
    assert result.can_be_used_in_suggestions is False
    assert result.blocks_suggestions is True


def test_deterministic_classification_unknown_fallback_stays_blocked() -> None:
    result = classify_document_deterministically(
        library_source_id="src-unknown",
        source_kind=ResearchLibrarySourceKind.UPLOADED_FILE,
        title="Bestand zonder duidelijk type",
        original_file_name="input.txt",
        extracted_text="willekeurige tekst",
        classified_at=NOW,
    )
    assert result.category == DeterministicDocumentCategory.UNKNOWN
    assert "fallback:unknown" in result.matched_signals
    assert result.can_be_used_in_research is False
    assert result.can_be_used_in_suggestions is False


def test_deterministic_classification_detects_annual_report_keywords() -> None:
    result = classify_document_deterministically(
        library_source_id="src-annual",
        source_kind=ResearchLibrarySourceKind.UPLOADED_FILE,
        title="ASML Annual Report 2025",
        original_file_name="asml-annual-report-2025.md",
        extracted_text="",
        classified_at=NOW,
    )
    assert result.category == DeterministicDocumentCategory.ANNUAL_REPORT
