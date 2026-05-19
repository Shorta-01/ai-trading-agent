from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

import pytest
from ai_trading_agent_storage import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
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
from fastapi.testclient import TestClient

from portfolio_outlook_api import research_sources
from portfolio_outlook_api.config import ResearchUploadSettings, StorageSettings
from portfolio_outlook_api.main import app

client = TestClient(app)


def _source_payload() -> dict[str, object]:
    return {
        "library_source_id": "src-1",
        "source_kind": "user",
        "status": "active",
        "classification_status": "pending",
        "extraction_status": "pending",
        "analysis_status": "pending",
        "asset_symbol": "ASML",
        "asset_name": "ASML",
        "title": "Bron",
        "document_type": "note",
        "source_type": "user_note",
        "source_credibility_level": None,
        "prompt_injection_risk_level": None,
        "content_hash_sha256": None,
        "archive_storage_uri": None,
        "raw_source_available": False,
        "schema_version": "v1",
        "explanation_nl": "test",
    }


def _uploaded_file_payload() -> dict[str, object]:
    return {
        "original_file_name": "a.pdf",
        "uploaded_by_user": True,
        "explanation_nl": "meta",
    }


def _url_payload() -> dict[str, object]:
    return {
        "url": "https://example.com",
        "user_supplied": True,
        "explanation_nl": "meta",
    }


def _document_set_payload() -> dict[str, object]:
    return {
        "document_set_id": "ds-1",
        "asset_symbol": "ASML",
        "title": "FY",
        "set_type": "yearly",
        "explanation_nl": "x",
    }


def _classification_payload() -> dict[str, object]:
    return {
        "classification_id": "c1",
        "document_type": "note",
        "source_type": "user_note",
        "confidence": "high",
        "needs_user_review": False,
        "reason_nl": "handmatig",
        "schema_version": "v1",
    }


def _asset_link_payload() -> dict[str, object]:
    return {
        "link_id": "l1",
        "link_type": "detected_new_asset",
        "mapping_confidence": "medium",
        "auto_linked": False,
        "requires_user_confirmation": True,
        "confirmed_by_user": False,
        "reason_nl": "detectie",
    }


def _processing_status_payload() -> dict[str, object]:
    return {
        "processing_id": "p1",
        "classification_status": "manual",
        "extraction_status": "none",
        "analysis_status": "none",
        "readiness_status": "blocked",
        "can_be_used_in_research": False,
        "can_be_used_in_suggestions": False,
        "needs_user_review": True,
        "blocks_suggestions": True,
        "reason_nl": "geen analyse",
    }


@pytest.fixture
def fake_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProvider:
        def __init__(self, _database_settings) -> None:
            pass

        @contextmanager
        def checked_connection(self, *, require_writable: bool) -> Iterator[object]:
            readiness = MigrationReadinessReport(
                status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
                database_connected=True,
                migrations_checked_against_database=True,
                offline_inventory_valid=True,
                latest_expected_revision_id="0010",
                database_revision_id="0010",
                persistence_allowed=True,
                blocks_runtime_writes=False,
                explanation_nl="Opslag is klaar voor metadata writes.",
            )
            yield type("Checked", (), {"connection": object(), "readiness": readiness})()

    class FakeRepository:
        def __init__(self, _connection, _readiness) -> None:
            self.sources: dict[str, ResearchSourceRecord] = {}
            self.uploaded_files: dict[str, ResearchUploadedFileMetadataRecord] = {}
            self.urls: dict[str, ResearchUrlMetadataRecord] = {}
            self.notes: dict[str, ResearchUserNoteRecord] = {}
            self.document_sets: dict[str, ResearchDocumentSetRecord] = {}
            self.members: dict[str, list[ResearchDocumentSetMemberRecord]] = defaultdict(list)
            self.classifications: dict[
                str, list[ResearchDocumentClassificationRecord]
            ] = defaultdict(list)
            self.links: dict[str, list[ResearchSourceAssetLinkRecord]] = defaultdict(list)
            self.processing: dict[
                str, list[ResearchSourceProcessingStatusRecord]
            ] = defaultdict(list)

        def save_research_source(self, record: ResearchSourceRecord) -> ResearchSourceRecord:
            self.sources[record.library_source_id] = record
            return record

        def get_research_source(self, library_source_id: str) -> ResearchSourceRecord | None:
            return self.sources.get(library_source_id)

        def list_research_sources_for_asset(
            self, asset_symbol: str
        ) -> tuple[ResearchSourceRecord, ...]:
            return tuple(r for r in self.sources.values() if r.asset_symbol == asset_symbol)

        def list_active_research_sources(self) -> tuple[ResearchSourceRecord, ...]:
            return tuple(r for r in self.sources.values() if r.status == "active")

        def save_uploaded_file_metadata(
            self, record: ResearchUploadedFileMetadataRecord
        ) -> ResearchUploadedFileMetadataRecord:
            self.uploaded_files[record.library_source_id] = record
            return record

        def get_uploaded_file_metadata(
            self, library_source_id: str
        ) -> ResearchUploadedFileMetadataRecord | None:
            return self.uploaded_files.get(library_source_id)

        def save_url_metadata(self, record: ResearchUrlMetadataRecord) -> ResearchUrlMetadataRecord:
            self.urls[record.library_source_id] = record
            return record

        def get_url_metadata(self, library_source_id: str) -> ResearchUrlMetadataRecord | None:
            return self.urls.get(library_source_id)

        def save_user_note(self, record: ResearchUserNoteRecord) -> ResearchUserNoteRecord:
            self.notes[record.library_source_id] = record
            return record

        def get_user_note(self, library_source_id: str) -> ResearchUserNoteRecord | None:
            return self.notes.get(library_source_id)

        def save_document_set(self, record: ResearchDocumentSetRecord) -> ResearchDocumentSetRecord:
            self.document_sets[record.document_set_id] = record
            return record

        def get_document_set(self, document_set_id: str) -> ResearchDocumentSetRecord | None:
            return self.document_sets.get(document_set_id)

        def save_document_set_member(
            self, record: ResearchDocumentSetMemberRecord
        ) -> ResearchDocumentSetMemberRecord:
            self.members[record.document_set_id].append(record)
            return record

        def list_document_set_members(
            self, document_set_id: str
        ) -> tuple[ResearchDocumentSetMemberRecord, ...]:
            return tuple(self.members.get(document_set_id, []))

        def save_document_classification(
            self, record: ResearchDocumentClassificationRecord
        ) -> ResearchDocumentClassificationRecord:
            self.classifications[record.library_source_id].append(record)
            return record

        def get_latest_classification(
            self, library_source_id: str
        ) -> ResearchDocumentClassificationRecord | None:
            records = self.classifications.get(library_source_id, [])
            return records[-1] if records else None

        def save_source_asset_link(
            self, record: ResearchSourceAssetLinkRecord
        ) -> ResearchSourceAssetLinkRecord:
            self.links[record.library_source_id].append(record)
            return record

        def list_asset_links_for_source(
            self, library_source_id: str
        ) -> tuple[ResearchSourceAssetLinkRecord, ...]:
            return tuple(self.links.get(library_source_id, []))

        def list_unconfirmed_detected_asset_links(
            self,
        ) -> tuple[ResearchSourceAssetLinkRecord, ...]:
            return tuple(
                link
                for records in self.links.values()
                for link in records
                if link.link_type == "detected_new_asset" and link.confirmed_by_user is False
            )

        def save_processing_status(
            self, record: ResearchSourceProcessingStatusRecord
        ) -> ResearchSourceProcessingStatusRecord:
            self.processing[record.library_source_id].append(record)
            return record

        def get_latest_processing_status(
            self, library_source_id: str
        ) -> ResearchSourceProcessingStatusRecord | None:
            records = self.processing.get(library_source_id, [])
            return records[-1] if records else None

    repo = FakeRepository(None, None)

    def repository_factory(_connection, _readiness):
        return repo

    monkeypatch.setattr(
        research_sources.settings,
        "storage",
        StorageSettings(enabled=True, database_url="sqlite+pysqlite:///:memory:"),
    )
    monkeypatch.setattr(research_sources, "StorageConnectionProvider", FakeProvider)
    monkeypatch.setattr(
        research_sources,
        "SqlAlchemyResearchSourceArchiveRepository",
        repository_factory,
    )


def _create_source() -> None:
    assert client.post("/research/sources", json=_source_payload()).status_code == 200


def test_storage_unavailable_safe() -> None:
    research_sources.settings.storage = StorageSettings(enabled=False, database_url=None)
    response = client.post(
        "/research/sources",
        json={
            "library_source_id": "x",
            "source_kind": "u",
            "status": "active",
            "classification_status": "p",
            "extraction_status": "p",
            "analysis_status": "p",
            "title": "t",
            "document_type": "d",
            "source_type": "s",
            "raw_source_available": False,
            "schema_version": "v1",
            "explanation_nl": "e",
        },
    )
    assert response.status_code == 503


def test_create_get_list_source_and_metadata_endpoints(fake_storage: None) -> None:
    _create_source()
    assert client.get("/research/sources/src-1").status_code == 200
    assert client.get("/research/sources", params={"asset_symbol": "ASML"}).status_code == 200

    uploaded_metadata_response = client.post(
        "/research/sources/src-1/uploaded-file-metadata",
        json=_uploaded_file_payload(),
    )
    assert uploaded_metadata_response.status_code == 200
    assert "niet geüpload" in uploaded_metadata_response.json()["message_nl"].lower()
    assert client.get("/research/sources/src-1/uploaded-file-metadata").status_code == 200

    url_metadata_response = client.post(
        "/research/sources/src-1/url-metadata",
        json=_url_payload(),
    )
    assert url_metadata_response.status_code == 200
    assert "niet opgehaald" in url_metadata_response.json()["message_nl"].lower()

    user_note_response = client.post(
        "/research/sources/src-1/user-note",
        json={"title": "n", "note_nl": "bewijs", "explanation_nl": "bew"},
    )
    assert user_note_response.status_code == 200
    assert "bewijs" in user_note_response.json()["message_nl"].lower()


def test_document_set_links_and_processing(fake_storage: None) -> None:
    _create_source()

    assert client.post("/research/document-sets", json=_document_set_payload()).status_code == 200
    assert (
        client.post(
            "/research/document-sets/ds-1/members",
            json={"member_id": "m1", "library_source_id": "src-1"},
        ).status_code
        == 200
    )
    assert client.get("/research/document-sets/ds-1/members").status_code == 200
    assert (
        client.post(
            "/research/sources/src-1/classifications",
            json=_classification_payload(),
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/research/sources/src-1/asset-links",
            json=_asset_link_payload(),
        ).status_code
        == 200
    )
    assert client.get("/research/asset-links/unconfirmed-detected").status_code == 200

    processing_status_response = client.post(
        "/research/sources/src-1/processing-status",
        json=_processing_status_payload(),
    )
    assert processing_status_response.status_code == 200
    assert "geen analyse gestart" in processing_status_response.json()["message_nl"].lower()


def _enable_uploads(tmp_path: Path, enabled: bool = True, max_bytes: int = 1024) -> None:
    research_sources.settings.research_upload = ResearchUploadSettings(
        enabled=enabled,
        archive_dir=str(tmp_path / "archive"),
        max_file_size_bytes=max_bytes,
        allowed_extensions=(".txt", ".pdf"),
        allowed_content_types=("text/plain", "application/pdf"),
    )


def test_upload_rejects_when_storage_disabled(tmp_path: Path) -> None:
    research_sources.settings.storage = StorageSettings(enabled=False, database_url=None)
    _enable_uploads(tmp_path)
    response = client.post(
        "/research/sources/src-a/upload-file",
        files={"file": ("a.txt", b"abc", "text/plain")},
    )
    assert response.status_code == 503


def test_upload_rejects_when_upload_feature_disabled(fake_storage: None, tmp_path: Path) -> None:
    _enable_uploads(tmp_path, enabled=False)
    response = client.post(
        "/research/sources/src-a/upload-file",
        files={"file": ("a.txt", b"abc", "text/plain")},
    )
    assert response.status_code == 503


def test_upload_txt_success_and_metadata(fake_storage: None, tmp_path: Path) -> None:
    _enable_uploads(tmp_path, max_bytes=10000)
    payload = b"bewijs-inhoud"
    response = client.post(
        "/research/sources/src-upload/upload-file",
        files={"file": ("../evil name.txt", payload, "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "nog niet gelezen" in body["message_nl"].lower()
    assert body["sha256"] == sha256(payload).hexdigest()
    assert "/archive/" in body["archive_storage_uri"]
    assert "/" not in body["stored_file_name"] and "\\" not in body["stored_file_name"]

    source = client.get("/research/sources/src-upload")
    assert source.status_code == 200
    assert source.json()["record"]["raw_source_available"] is True

    file_meta = client.get("/research/sources/src-upload/uploaded-file-metadata")
    assert file_meta.status_code == 200
    assert file_meta.json()["record"]["file_hash_sha256"] == sha256(payload).hexdigest()

    status = client.get("/research/sources/src-upload/processing-status")
    assert status.status_code == 200
    record = status.json()["record"]
    assert record["blocks_suggestions"] is True
    assert record["can_be_used_in_suggestions"] is False


def test_upload_rejects_path_traversal_names(fake_storage: None, tmp_path: Path) -> None:
    _enable_uploads(tmp_path)
    for name in ("../evil.pdf", "folder/evil.pdf", "folder\\evil.pdf"):
        response = client.post(
            "/research/sources/src-path/upload-file",
            files={"file": (name, b"x", "application/pdf")},
        )
        assert response.status_code == 400


def test_upload_rejects_unsupported_extension_oversize_and_empty_name(
    fake_storage: None,
    tmp_path: Path,
) -> None:
    _enable_uploads(tmp_path, max_bytes=2)
    unsupported = client.post(
        "/research/sources/src-unsupported/upload-file",
        files={"file": ("a.exe", b"abc", "application/octet-stream")},
    )
    assert unsupported.status_code == 400

    oversized = client.post(
        "/research/sources/src-big/upload-file",
        files={"file": ("a.txt", b"abcd", "text/plain")},
    )
    assert oversized.status_code == 413

    empty_name = client.post(
        "/research/sources/src-empty/upload-file",
        files={"file": ("", b"abc", "text/plain")},
    )
    assert empty_name.status_code == 400
