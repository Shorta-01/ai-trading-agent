from fastapi.testclient import TestClient

from portfolio_outlook_api.config import StorageSettings, settings
from portfolio_outlook_api.main import app

client = TestClient(app)


def _enable_storage() -> None:
    settings.storage = StorageSettings(
        enabled=True,
        database_url="sqlite+pysqlite:///:memory:",
    )


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


def _create_source() -> None:
    assert client.post("/research/sources", json=_source_payload()).status_code == 200


def test_storage_unavailable_safe() -> None:
    settings.storage = StorageSettings(enabled=False, database_url=None)
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


def test_create_get_list_source_and_metadata_endpoints() -> None:
    _enable_storage()
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


def test_document_set_links_and_processing() -> None:
    _enable_storage()
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
