"""Endpoint tests for ``POST /research/sources/{id}/ai-extract``.

The endpoint reads the worker-archived plain-text extraction, feeds
it through the provider, and runs every fact through
:func:`validate_extracted_facts`. The tests cover the empty-state
cascade (disabled / not_configured / source missing / extraction
missing) and a stub happy path that proves the safety pipeline is end-
to-end wired.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from ai_trading_agent_storage import (
    ResearchExtractedTextRecord,
    ResearchSourceRecord,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api import research_ai_extraction_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_NOW = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.research_ai_extraction_enabled = False
    api_settings.research_ai_extraction_provider_code = "stub"
    api_settings.research_ai_extraction_max_facts = 12
    api_settings.research_ai_extraction_max_fact_chars = 500


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _source(library_source_id: str = "src-1") -> ResearchSourceRecord:
    return ResearchSourceRecord(
        library_source_id=library_source_id,
        source_kind="uploaded_file",
        status="active",
        classification_status="pending",
        extraction_status="extracted",
        analysis_status="not_started",
        asset_symbol="AAPL",
        asset_name="Apple Inc.",
        title="Q1 2025 Earnings",
        document_type="earnings",
        source_type="filing",
        source_credibility_level="high",
        prompt_injection_risk_level="low",
        content_hash_sha256="content-hash",
        archive_storage_uri="file:///tmp/src-1.txt",
        raw_source_available=True,
        created_at=_NOW,
        updated_at=_NOW,
        archived_at=None,
        schema_version="v1",
        explanation_nl="Test source.",
    )


def _extracted(
    storage_uri: str | None = "file:///tmp/extracted-src-1.txt",
) -> ResearchExtractedTextRecord:
    return ResearchExtractedTextRecord(
        extracted_text_id="ext-1",
        library_source_id="src-1",
        source_file_hash_sha256="src-hash",
        extraction_status="extracted",
        extraction_method="deterministic_plain_text_v1",
        detected_content_type="text/plain",
        detected_language="en",
        character_count=200,
        line_count=5,
        text_hash_sha256="text-hash",
        extracted_text_storage_uri=storage_uri,
        preview_text_nl="Apple Inc. Q1 2025 Earnings.",
        can_be_used_in_research=False,
        can_be_used_in_suggestions=False,
        needs_user_review=True,
        blocks_suggestions=True,
        created_at=_NOW,
        extracted_at=_NOW,
        schema_version="v1",
        reason_nl="x",
    )


def _install_fake_storage(
    monkeypatch,
    *,
    source: ResearchSourceRecord | None,
    extracted: ResearchExtractedTextRecord | None,
) -> None:
    class _FakeConn:
        pass

    class _Checked:
        connection = _FakeConn()
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Checked()

        def __exit__(self, *_):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    class _FakeRepo:
        def get_research_source(self, _sid):
            return source

        def get_latest_extracted_text_for_source(self, _sid):
            return extracted

    monkeypatch.setattr(
        research_ai_extraction_routes,
        "StorageConnectionProvider",
        _FakeStorageProvider,
    )
    monkeypatch.setattr(
        research_ai_extraction_routes,
        "build_database_connection_settings",
        lambda _u: object(),
    )
    monkeypatch.setattr(
        research_ai_extraction_routes,
        "SqlAlchemyResearchSourceArchiveRepository",
        lambda *a, **k: _FakeRepo(),
    )


def test_returns_disabled_when_flag_off() -> None:
    r = client.post("/research/sources/src-1/ai-extract")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "disabled"
    assert body["facts"] == []
    assert body["safe_for_orders"] is False
    assert body["safe_for_suggestions"] is False


def test_returns_not_configured_when_storage_disabled() -> None:
    api_settings.research_ai_extraction_enabled = True
    r = client.post("/research/sources/src-1/ai-extract")
    body = r.json()
    assert body["status"] == "not_configured"


def test_returns_404_when_source_missing(monkeypatch) -> None:
    api_settings.research_ai_extraction_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _install_fake_storage(monkeypatch, source=None, extracted=None)

    r = client.post("/research/sources/src-missing/ai-extract")
    assert r.status_code == 404


def test_returns_no_extracted_text_when_extract_missing(monkeypatch) -> None:
    api_settings.research_ai_extraction_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _install_fake_storage(monkeypatch, source=_source(), extracted=None)

    r = client.post("/research/sources/src-1/ai-extract")
    body = r.json()
    assert body["status"] == "no_extracted_text"
    assert body["facts"] == []


def test_happy_path_with_stub_provider(monkeypatch, tmp_path) -> None:
    api_settings.research_ai_extraction_enabled = True
    api_settings.research_ai_extraction_provider_code = "stub"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"

    # Point the path-resolution root at our tmp dir so the URI under
    # tmp_path is accepted as inside the configured archive.
    api_settings.research_extraction.extracted_text_archive_dir = str(tmp_path)
    text_path = tmp_path / "extracted-src-1.txt"
    text_path.write_text(
        "Apple Inc. Q1 2025 Earnings.\n"
        "Revenue rose to 124.3 billion USD.\n"
        "Services revenue grew 18%.\n",
        encoding="utf-8",
    )
    _install_fake_storage(
        monkeypatch,
        source=_source(),
        extracted=_extracted(storage_uri=f"file://{text_path}"),
    )

    r = client.post("/research/sources/src-1/ai-extract")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "generated"
    assert body["model_provider_code"] == "stub"
    assert body["blocking_reason"] is None
    assert body["hallucinated_fact_indices"] == []
    # Stub picks the first N non-empty source lines verbatim, so every
    # fact is grounded by construction.
    assert len(body["facts"]) >= 1
    assert all(f["is_grounded"] for f in body["facts"])
    assert body["safe_for_orders"] is False
    assert body["safe_for_suggestions"] is False
    # Source hash is computed deterministically from the file contents,
    # exposed so the operator (and any follow-up persistence layer) can
    # bind extracted facts back to the exact source text they came from.
    assert isinstance(body["source_text_hash"], str)
    assert len(body["source_text_hash"]) == 64  # sha256 hex


def test_path_traversal_in_storage_uri_is_blocked(monkeypatch, tmp_path) -> None:
    """A crafted ``file://`` URI that escapes the configured archive
    root must be rejected — the existing extractor applies the same
    defence on writes; we mirror it on reads."""

    api_settings.research_ai_extraction_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.research_extraction.extracted_text_archive_dir = str(tmp_path)

    outside_path = tmp_path.parent / "evil.txt"
    outside_path.write_text("secrets", encoding="utf-8")

    _install_fake_storage(
        monkeypatch,
        source=_source(),
        extracted=_extracted(storage_uri=f"file://{outside_path}"),
    )

    r = client.post("/research/sources/src-1/ai-extract")
    assert r.status_code == 400


def test_unknown_provider_code_yields_provider_unavailable(monkeypatch, tmp_path) -> None:
    api_settings.research_ai_extraction_enabled = True
    api_settings.research_ai_extraction_provider_code = "openai_gpt4"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.research_extraction.extracted_text_archive_dir = str(tmp_path)
    text_path = tmp_path / "extracted-src-1.txt"
    text_path.write_text("Some text.", encoding="utf-8")
    _install_fake_storage(
        monkeypatch,
        source=_source(),
        extracted=_extracted(storage_uri=f"file://{text_path}"),
    )

    r = client.post("/research/sources/src-1/ai-extract")
    body = r.json()
    assert body["status"] == "provider_unavailable"
    assert body["blocking_reason"] == "real_client_not_implemented"
    assert body["source_text_hash"] is not None  # the file WAS read


@pytest.fixture(autouse=True)
def _restore_archive_dir():
    """The extracted-text-archive-dir is a process-wide setting; reset
    it between tests so leaks don't change paths in unrelated routes."""

    original = api_settings.research_extraction.extracted_text_archive_dir
    yield
    api_settings.research_extraction.extracted_text_archive_dir = original
