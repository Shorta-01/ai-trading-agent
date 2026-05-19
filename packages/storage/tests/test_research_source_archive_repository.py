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
    ResearchSourceAssetLinkRecord,
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
        latest_expected_revision_id="0010",
        database_revision_id="0010",
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
