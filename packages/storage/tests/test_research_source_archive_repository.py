from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine

from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from ai_trading_agent_storage.repository_contracts import (
    ResearchDocumentClassificationRecord,
    ResearchDocumentSetMemberRecord,
    ResearchDocumentSetRecord,
    ResearchExtractedTextRecord,
    ResearchSourceAssetLinkRecord,
    ResearchSourceCredibilityAssessmentRecord,
    ResearchSourceEvidenceItemRecord,
    ResearchSourceEvidenceLedgerLinkRecord,
    ResearchSourceProcessingStatusRecord,
    ResearchSourceRecord,
    ResearchUploadedFileMetadataRecord,
    ResearchUrlMetadataRecord,
    ResearchUserNoteRecord,
)
from ai_trading_agent_storage.sql_repositories import SqlAlchemyResearchSourceArchiveRepository


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0011",
        database_revision_id="0011",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _source(
    source_id: str, *, asset_symbol: str | None = None, archived: bool = False
) -> ResearchSourceRecord:
    now = datetime.now(UTC)
    return ResearchSourceRecord(
        library_source_id=source_id,
        source_kind="upload",
        status="active" if not archived else "archived",
        classification_status="pending",
        extraction_status="pending",
        analysis_status="pending",
        asset_symbol=asset_symbol,
        asset_name=None,
        title="Titel",
        document_type="financial_report",
        source_type="company_filing",
        source_credibility_level=None,
        prompt_injection_risk_level=None,
        content_hash_sha256=None,
        archive_storage_uri=None,
        raw_source_available=True,
        created_at=now,
        updated_at=now,
        archived_at=now if archived else None,
        schema_version="1.0",
        explanation_nl="Bron",
    )


def test_archive_repository_roundtrips_and_filters() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyResearchSourceArchiveRepository(conn, _report())

        s1 = _source("src-1", asset_symbol="ASML")
        s2 = _source("src-2", asset_symbol="ASML", archived=True)
        s3 = _source("src-3", asset_symbol="AAPL")
        repo.save_research_source(s1)
        repo.save_research_source(s2)
        repo.save_research_source(s3)

        loaded_source = repo.get_research_source("src-1")
        assert loaded_source is not None
        assert loaded_source.library_source_id == s1.library_source_id
        assert loaded_source.asset_symbol == s1.asset_symbol
        assert {r.library_source_id for r in repo.list_research_sources_for_asset("ASML")} == {
            "src-1",
            "src-2",
        }
        assert {r.library_source_id for r in repo.list_active_research_sources()} == {
            "src-1",
            "src-3",
        }

        up = ResearchUploadedFileMetadataRecord(
            "src-1", "a.pdf", None, None, 100, None, None, 2, datetime.now(UTC), True, "up"
        )
        repo.save_uploaded_file_metadata(up)
        loaded_upload = repo.get_uploaded_file_metadata("src-1")
        assert loaded_upload is not None
        assert loaded_upload.library_source_id == up.library_source_id

        url = ResearchUrlMetadataRecord(
            "src-1", "https://x", None, None, None, None, None, None, None, True, "url"
        )
        repo.save_url_metadata(url)
        loaded_url = repo.get_url_metadata("src-1")
        assert loaded_url is not None
        assert loaded_url.url == url.url

        note = ResearchUserNoteRecord(
            "src-1", "ASML", "t", "n", None, None, datetime.now(UTC), datetime.now(UTC), "note"
        )
        repo.save_user_note(note)
        loaded_note = repo.get_user_note("src-1")
        assert loaded_note is not None
        assert loaded_note.note_nl == note.note_nl

        dset = ResearchDocumentSetRecord(
            "set-1", "ASML", "Set", "periodic", datetime.now(UTC), "set"
        )
        repo.save_document_set(dset)
        loaded_set = repo.get_document_set("set-1")
        assert loaded_set is not None
        assert loaded_set.document_set_id == dset.document_set_id

        older = datetime.now(UTC) - timedelta(minutes=1)
        m2 = ResearchDocumentSetMemberRecord("m2", "set-1", "src-3", None, None, 2, older)
        m1 = ResearchDocumentSetMemberRecord(
            "m1", "set-1", "src-1", None, None, 1, datetime.now(UTC)
        )
        repo.save_document_set_member(m2)
        repo.save_document_set_member(m1)
        assert [m.member_id for m in repo.list_document_set_members("set-1")] == ["m1", "m2"]

        c1 = ResearchDocumentClassificationRecord(
            "c1", "src-1", "d", "s", "high", None, None, None, None, None, False, "r", older, "1"
        )
        c2 = ResearchDocumentClassificationRecord(
            "c2",
            "src-1",
            "d",
            "s",
            "high",
            None,
            None,
            None,
            None,
            None,
            False,
            "r",
            datetime.now(UTC),
            "1",
        )
        repo.save_document_classification(c1)
        repo.save_document_classification(c2)
        latest_classification = repo.get_latest_classification("src-1")
        assert latest_classification is not None
        assert latest_classification.classification_id == c2.classification_id

        link1 = ResearchSourceAssetLinkRecord(
            "l1",
            "src-1",
            "ASML",
            None,
            None,
            None,
            "detected_new_asset",
            "high",
            True,
            True,
            False,
            "r",
            datetime.now(UTC),
            None,
        )
        link2 = ResearchSourceAssetLinkRecord(
            "l2",
            "src-1",
            "AAPL",
            None,
            None,
            None,
            "portfolio_existing_asset",
            "high",
            True,
            False,
            False,
            "r",
            datetime.now(UTC),
            None,
        )
        link3 = ResearchSourceAssetLinkRecord(
            "l3",
            "src-3",
            "TSLA",
            None,
            None,
            None,
            "detected_new_asset",
            "high",
            True,
            True,
            True,
            "r",
            datetime.now(UTC),
            datetime.now(UTC),
        )
        repo.save_source_asset_link(link1)
        repo.save_source_asset_link(link2)
        repo.save_source_asset_link(link3)
        assert {link.link_id for link in repo.list_asset_links_for_source("src-1")} == {"l1", "l2"}
        assert {link.link_id for link in repo.list_unconfirmed_detected_asset_links()} == {"l1"}

        p1 = ResearchSourceProcessingStatusRecord(
            "p1", "src-1", "a", "b", "c", "blocked", False, False, True, True, "e", older, "r"
        )
        p2 = ResearchSourceProcessingStatusRecord(
            "p2",
            "src-1",
            "a",
            "b",
            "c",
            "ready",
            True,
            True,
            False,
            False,
            None,
            datetime.now(UTC),
            "r",
        )
        repo.save_processing_status(p1)
        repo.save_processing_status(p2)
        latest_processing = repo.get_latest_processing_status("src-1")
        assert latest_processing is not None
        assert latest_processing.processing_id == p2.processing_id

        e1 = ResearchExtractedTextRecord(
            "ext-1", "src-1", None, "pending", "manual_record", None, "nl", 10, 1, None, None,
            "preview", False, False, True, True, older, None, "1.0", "Wachten op extractie."
        )
        e2 = ResearchExtractedTextRecord(
            "ext-2", "src-1", None, "extracted", "deterministic_text_extraction", "text/plain",
            "nl", 120, 8, "hash", "archive://x", "preview2", True, False, False, False,
            datetime(2026, 1, 2, tzinfo=UTC), datetime(2026, 1, 3, tzinfo=UTC), "1.0", "Klaar."
        )
        e3 = ResearchExtractedTextRecord(
            "ext-3", "src-2", None, "extracted", "deterministic_text_extraction", "text/plain",
            "nl", 20, 2, None, None, None, True, False, False, False,
            datetime(2026, 1, 2, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC), "1.0", "Klaar."
        )
        repo.save_extracted_text(e1)
        repo.save_extracted_text(e2)
        repo.save_extracted_text(e3)
        loaded_extracted = repo.get_extracted_text("ext-1")
        assert loaded_extracted is not None
        assert loaded_extracted.extracted_text_id == "ext-1"
        assert [x.extracted_text_id for x in repo.list_extracted_texts_for_source("src-1")] == [
            "ext-2",
            "ext-1",
        ]
        latest_extracted = repo.get_latest_extracted_text_for_source("src-1")
        assert latest_extracted is not None
        assert latest_extracted.extracted_text_id == "ext-2"

        ev = ResearchSourceEvidenceItemRecord(
            evidence_item_id="evidence-1",
            library_source_id="src-1",
            evidence_type="financial_statement_fact",
            evidence_status="registered",
            extracted_from_kind="manual",
            source_reference_text="Omzet steeg 5%",
            normalized_evidence_text="omzet steeg 5 procent",
            evidence_summary_nl="Omzetgroei",
            asset_symbol="ASML",
            reporting_period="Q4",
            fiscal_year=2025,
            confidence_level="medium",
            extraction_method="deterministic_manual_payload",
            source_text_hash_sha256=None,
            extraction_run_id=None,
            created_at=datetime(2026, 1, 4, tzinfo=UTC),
            extracted_at=datetime(2026, 1, 3, tzinfo=UTC),
            safe_to_use_as_evidence=True,
            safe_to_use_for_suggestions=False,
            blocks_suggestions=True,
            explanation_nl="Alleen bewijs",
        )
        repo.save_source_evidence_item(ev)
        evidence = repo.list_source_evidence_items("src-1")
        assert len(evidence) == 1
        assert evidence[0].safe_to_use_for_suggestions is False
        ledger_link = ResearchSourceEvidenceLedgerLinkRecord(
            link_id="lnk-1",
            library_source_id="src-1",
            evidence_item_id="evidence-1",
            evidence_ledger_item_id="ledger-1",
            link_type="source_lineage",
            link_status="registered",
            created_at=datetime.now(UTC),
            created_by_system="tests",
            lineage_scope="source_to_ledger",
            source_snapshot_reference=None,
            evidence_text_hash_sha256=None,
            gate_context_status="blocked_pending_gates",
            safe_to_use_for_suggestions=False,
            blocks_suggestions=True,
            explanation_nl="Auditlink",
        )
        repo.save_source_evidence_ledger_link(ledger_link)
        assert len(repo.list_source_evidence_ledger_links("src-1")) == 1
        assert len(repo.list_evidence_item_ledger_links("evidence-1")) == 1


def test_source_credibility_assessment_roundtrip_latest() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyResearchSourceArchiveRepository(conn, _report())
        repo.save_research_source(_source("src-cred"))
        older = datetime.now(UTC) - timedelta(minutes=1)
        c1 = ResearchSourceCredibilityAssessmentRecord(
            assessment_id="cred-1", library_source_id="src-cred", credibility_status="assessed",
            credibility_level="medium",
            source_category="news",
            assessed_at=older,
            checked_at=older,
            confidence_level="medium",
            credibility_signals_json=("x",),
            limitation_notes_nl=None,
            safe_to_use_as_evidence=False,
            safe_to_use_for_suggestions=False,
            blocks_suggestions=True,
            explanation_nl="Geblokkeerd",
        )
        c2 = ResearchSourceCredibilityAssessmentRecord(
            assessment_id="cred-2", library_source_id="src-cred", credibility_status="assessed",
            credibility_level="high",
            source_category="filing",
            assessed_at=datetime.now(UTC),
            checked_at=datetime.now(UTC),
            confidence_level="high",
            credibility_signals_json=("official",),
            limitation_notes_nl="Alleen bewijs",
            safe_to_use_as_evidence=True,
            safe_to_use_for_suggestions=False,
            blocks_suggestions=True,
            explanation_nl="Nog steeds geblokkeerd",
        )
        repo.save_source_credibility_assessment(c1)
        repo.save_source_credibility_assessment(c2)
        latest = repo.get_latest_source_credibility_assessment("src-cred")
        assert latest is not None
        assert latest.assessment_id == "cred-2"
        assert latest.blocks_suggestions is True
