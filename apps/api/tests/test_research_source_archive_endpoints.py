from fastapi.testclient import TestClient

from portfolio_outlook_api.config import StorageSettings, settings
from portfolio_outlook_api.main import app

client = TestClient(app)


def _enable_storage() -> None:
    settings.storage = StorageSettings(enabled=True, database_url="sqlite+pysqlite:///:memory:")


def _create_source() -> None:
    payload = {
        "library_source_id": "src-1", "source_kind": "user", "status": "active", "classification_status": "pending", "extraction_status": "pending", "analysis_status": "pending", "asset_symbol": "ASML", "asset_name": "ASML", "title": "Bron", "document_type": "note", "source_type": "user_note", "source_credibility_level": None, "prompt_injection_risk_level": None, "content_hash_sha256": None, "archive_storage_uri": None, "raw_source_available": False, "schema_version": "v1", "explanation_nl": "test"
    }
    assert client.post("/research/sources", json=payload).status_code == 200


def test_storage_unavailable_safe() -> None:
    settings.storage = StorageSettings(enabled=False, database_url=None)
    r = client.post("/research/sources", json={"library_source_id": "x", "source_kind": "u", "status": "active", "classification_status": "p", "extraction_status": "p", "analysis_status": "p", "title": "t", "document_type": "d", "source_type": "s", "raw_source_available": False, "schema_version": "v1", "explanation_nl": "e"})
    assert r.status_code == 503


def test_create_get_list_source_and_metadata_endpoints() -> None:
    _enable_storage()
    _create_source()
    assert client.get("/research/sources/src-1").status_code == 200
    assert client.get("/research/sources", params={"asset_symbol": "ASML"}).status_code == 200

    rf = client.post("/research/sources/src-1/uploaded-file-metadata", json={"original_file_name": "a.pdf", "uploaded_by_user": True, "explanation_nl": "meta"})
    assert rf.status_code == 200
    assert "niet geüpload" in rf.json()["message_nl"].lower()
    assert client.get("/research/sources/src-1/uploaded-file-metadata").status_code == 200

    ru = client.post("/research/sources/src-1/url-metadata", json={"url": "https://example.com", "user_supplied": True, "explanation_nl": "meta"})
    assert ru.status_code == 200
    assert "niet opgehaald" in ru.json()["message_nl"].lower()

    rn = client.post("/research/sources/src-1/user-note", json={"title": "n", "note_nl": "bewijs", "explanation_nl": "bew"})
    assert rn.status_code == 200
    assert "bewijs" in rn.json()["message_nl"].lower()


def test_document_set_links_and_processing() -> None:
    _enable_storage(); _create_source()
    assert client.post("/research/document-sets", json={"document_set_id": "ds-1", "asset_symbol": "ASML", "title": "FY", "set_type": "yearly", "explanation_nl": "x"}).status_code == 200
    assert client.post("/research/document-sets/ds-1/members", json={"member_id": "m1", "library_source_id": "src-1"}).status_code == 200
    assert client.get("/research/document-sets/ds-1/members").status_code == 200
    assert client.post("/research/sources/src-1/classifications", json={"classification_id": "c1", "document_type": "note", "source_type": "user_note", "confidence": "high", "needs_user_review": False, "reason_nl": "handmatig", "schema_version": "v1"}).status_code == 200
    assert client.post("/research/sources/src-1/asset-links", json={"link_id": "l1", "link_type": "detected_new_asset", "mapping_confidence": "medium", "auto_linked": False, "requires_user_confirmation": True, "confirmed_by_user": False, "reason_nl": "detectie"}).status_code == 200
    assert client.get("/research/asset-links/unconfirmed-detected").status_code == 200
    ps = client.post("/research/sources/src-1/processing-status", json={"processing_id": "p1", "classification_status": "manual", "extraction_status": "none", "analysis_status": "none", "readiness_status": "blocked", "can_be_used_in_research": False, "can_be_used_in_suggestions": False, "needs_user_review": True, "blocks_suggestions": True, "reason_nl": "geen analyse"})
    assert ps.status_code == 200
    assert "geen analyse gestart" in ps.json()["message_nl"].lower()
