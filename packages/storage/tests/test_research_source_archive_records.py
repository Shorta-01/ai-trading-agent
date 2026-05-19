from dataclasses import fields
from datetime import UTC, datetime

import pytest

from ai_trading_agent_storage.repository_contracts import (
    ResearchDocumentClassificationRecord,
    ResearchDocumentSetMemberRecord,
    ResearchDocumentSetRecord,
    ResearchSourceAssetLinkRecord,
    ResearchSourceProcessingStatusRecord,
    ResearchSourceRecord,
    ResearchUploadedFileMetadataRecord,
    ResearchUrlMetadataRecord,
    ResearchUserNoteRecord,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _source(**overrides: object) -> ResearchSourceRecord:
    data: dict[str, object] = {
        "library_source_id": "src-1",
        "source_kind": "upload",
        "status": "active",
        "classification_status": "pending",
        "extraction_status": "pending",
        "analysis_status": "pending",
        "asset_symbol": None,
        "asset_name": None,
        "title": "Q1 Report",
        "document_type": "financial_report",
        "source_type": "company_filing",
        "source_credibility_level": None,
        "prompt_injection_risk_level": None,
        "content_hash_sha256": None,
        "archive_storage_uri": None,
        "raw_source_available": True,
        "created_at": _now(),
        "updated_at": _now(),
        "archived_at": None,
        "schema_version": "1.0",
        "explanation_nl": "Bron opgeslagen.",
    }
    data.update(overrides)
    return ResearchSourceRecord(**data)


def test_research_source_record_validation() -> None:
    with pytest.raises(ValueError):
        _source(library_source_id="")
    with pytest.raises(ValueError):
        _source(title="")
    with pytest.raises(ValueError):
        _source(explanation_nl="")
    with pytest.raises(ValueError):
        _source(
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    with pytest.raises(ValueError):
        _source(
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
            archived_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_uploaded_file_metadata_validation() -> None:
    base = dict(
        library_source_id="src-1",
        original_file_name="report.pdf",
        stored_file_name=None,
        content_type=None,
        file_size_bytes=None,
        file_hash_sha256=None,
        detected_language=None,
        page_count=None,
        uploaded_at=_now(),
        uploaded_by_user=True,
        explanation_nl="Bestand metadata.",
    )
    with pytest.raises(ValueError):
        ResearchUploadedFileMetadataRecord(**(base | {"original_file_name": ""}))
    with pytest.raises(ValueError):
        ResearchUploadedFileMetadataRecord(**(base | {"file_size_bytes": 0}))
    with pytest.raises(ValueError):
        ResearchUploadedFileMetadataRecord(**(base | {"page_count": 0}))


def test_url_metadata_validation() -> None:
    base = dict(
        library_source_id="src-1",
        url="https://example.com/report",
        normalized_url=None,
        domain=None,
        fetched_at=None,
        snapshot_hash_sha256=None,
        snapshot_storage_uri=None,
        http_status_code=None,
        content_type=None,
        user_supplied=True,
        explanation_nl="URL metadata.",
    )
    with pytest.raises(ValueError):
        ResearchUrlMetadataRecord(**(base | {"url": ""}))
    with pytest.raises(ValueError):
        ResearchUrlMetadataRecord(**(base | {"http_status_code": 99}))
    with pytest.raises(ValueError):
        ResearchUrlMetadataRecord(**(base | {"http_status_code": 600}))


def test_user_note_validation() -> None:
    now = _now()
    with pytest.raises(ValueError):
        ResearchUserNoteRecord(
            library_source_id="src-1",
            asset_symbol=None,
            title="Notitie",
            note_nl="",
            thesis_relevance_nl=None,
            user_confidence_nl=None,
            created_at=now,
            updated_at=now,
            explanation_nl="Notitie bewaard.",
        )
    with pytest.raises(ValueError):
        ResearchUserNoteRecord(
            library_source_id="src-1",
            asset_symbol=None,
            title="Notitie",
            note_nl="Tekst",
            thesis_relevance_nl=None,
            user_confidence_nl=None,
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            explanation_nl="Notitie bewaard.",
        )


def test_document_set_and_member_validation() -> None:
    with pytest.raises(ValueError):
        ResearchDocumentSetRecord("", "AAPL", "Set", "periodic", _now(), "Uitleg")
    with pytest.raises(ValueError):
        ResearchDocumentSetRecord("set-1", "", "Set", "periodic", _now(), "Uitleg")

    with pytest.raises(ValueError):
        ResearchDocumentSetMemberRecord("m-1", "", "src-1", None, None, None, _now())
    with pytest.raises(ValueError):
        ResearchDocumentSetMemberRecord("m-1", "set-1", "", None, None, None, _now())
    with pytest.raises(ValueError):
        ResearchDocumentSetMemberRecord("m-1", "set-1", "src-1", None, None, -1, _now())


def test_classification_asset_link_and_processing_validation() -> None:
    base_classification = dict(
        classification_id="c-1",
        library_source_id="src-1",
        document_type="financial_report",
        source_type="filing",
        confidence="high",
        detected_asset_symbol=None,
        detected_asset_name=None,
        detected_fiscal_year=None,
        detected_reporting_period=None,
        detected_language=None,
        needs_user_review=False,
        reason_nl="Geklasseerd.",
        classified_at=_now(),
        schema_version="1.0",
    )
    with pytest.raises(ValueError):
        ResearchDocumentClassificationRecord(**(base_classification | {"reason_nl": ""}))
    with pytest.raises(ValueError):
        ResearchDocumentClassificationRecord(**(base_classification | {"schema_version": ""}))

    with pytest.raises(ValueError):
        ResearchSourceAssetLinkRecord(
            link_id="l-1",
            library_source_id="src-1",
            asset_symbol=None,
            asset_name=None,
            conid=None,
            isin=None,
            link_type="detected",
            mapping_confidence="high",
            auto_linked=True,
            requires_user_confirmation=False,
            confirmed_by_user=False,
            reason_nl="",
            created_at=_now(),
            confirmed_at=None,
        )
    with pytest.raises(ValueError):
        ResearchSourceAssetLinkRecord(
            link_id="l-1",
            library_source_id="src-1",
            asset_symbol=None,
            asset_name=None,
            conid=None,
            isin=None,
            link_type="detected",
            mapping_confidence="high",
            auto_linked=True,
            requires_user_confirmation=False,
            confirmed_by_user=False,
            reason_nl="Gekoppeld",
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
            confirmed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

    with pytest.raises(ValueError):
        ResearchSourceProcessingStatusRecord(
            processing_id="p-1",
            library_source_id="src-1",
            classification_status="done",
            extraction_status="done",
            analysis_status="done",
            readiness_status="ready",
            can_be_used_in_research=True,
            can_be_used_in_suggestions=True,
            needs_user_review=False,
            blocks_suggestions=False,
            last_error_nl=None,
            checked_at=_now(),
            reason_nl="",
        )
    with pytest.raises(ValueError):
        ResearchSourceProcessingStatusRecord(
            processing_id="p-1",
            library_source_id="src-1",
            classification_status="done",
            extraction_status="done",
            analysis_status="done",
            readiness_status="blocked",
            can_be_used_in_research=False,
            can_be_used_in_suggestions=True,
            needs_user_review=True,
            blocks_suggestions=True,
            last_error_nl="Fout",
            checked_at=_now(),
            reason_nl="Geblokkeerd",
        )


def test_contracts_do_not_expose_bytes_or_credentials_or_keys() -> None:
    forbidden = ("raw_file_bytes", "openai_key", "ibkr_credential", "api_key", "secret")
    for contract in (
        ResearchSourceRecord,
        ResearchUploadedFileMetadataRecord,
        ResearchUrlMetadataRecord,
        ResearchUserNoteRecord,
        ResearchDocumentSetRecord,
        ResearchDocumentSetMemberRecord,
        ResearchDocumentClassificationRecord,
        ResearchSourceAssetLinkRecord,
        ResearchSourceProcessingStatusRecord,
    ):
        for field in fields(contract):
            lower = field.name.lower()
            assert not any(token in lower for token in forbidden)
