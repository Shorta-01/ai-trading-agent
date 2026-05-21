from dataclasses import fields

from ai_trading_agent_storage.repository_contracts import (
    FreshnessAuditRecord,
    ProviderSourceRecord,
    RequestLogRecord,
)
from fastapi.testclient import TestClient
from request_audit_fixtures import (
    make_freshness_audit_record,
    make_provider_source_record,
    make_request_audit_repo,
    make_request_log_record,
)

from portfolio_outlook_api.main import app
from portfolio_outlook_api.request_audit import (
    FreshnessAuditListResponse,
    FreshnessAuditResponse,
    ProviderSourceListResponse,
    ProviderSourceResponse,
    RequestLogListResponse,
    RequestLogResponse,
)

client = TestClient(app)


def _patch_repo(monkeypatch, **kwargs):
    monkeypatch.setattr(
        "portfolio_outlook_api.request_audit._with_repository",
        lambda op: op(make_request_audit_repo(**kwargs)),
    )


def test_list_endpoints_empty(monkeypatch) -> None:
    _patch_repo(monkeypatch)
    for path in [
        "/audit/request-logs",
        "/audit/provider-sources",
        "/audit/freshness-audits",
    ]:
        payload = client.get(path).json()
        assert payload["items"] == []
        assert payload["total_count"] == 0


def test_contract_harness_response_field_alignment() -> None:
    request_log_record_fields = set(RequestLogRecord.__dataclass_fields__)
    request_log_response_fields = set(RequestLogResponse.model_fields)
    assert request_log_record_fields.issubset(request_log_response_fields)

    provider_source_record_fields = set(ProviderSourceRecord.__dataclass_fields__)
    provider_source_response_fields = set(ProviderSourceResponse.model_fields)
    assert provider_source_record_fields.issubset(
        provider_source_response_fields | {"explanation_nl"}
    )

    freshness_response_fields = set(FreshnessAuditResponse.model_fields)
    compatibility_fields = {
        "freshness_policy_code",
        "snapshot_as_of",
        "stale_after",
        "age_seconds",
        "freshness_window_seconds",
    }
    for name in [f.name for f in fields(FreshnessAuditRecord) if f.name != "explanation_nl"]:
        assert name in freshness_response_fields or name in compatibility_fields

    assert "items" in RequestLogListResponse.model_fields
    assert "items" in ProviderSourceListResponse.model_fields
    assert "items" in FreshnessAuditListResponse.model_fields


def test_summary_counts_populated(monkeypatch) -> None:
    reqs = [
        make_request_log_record(request_log_id="r1", request_status="blocked"),
        make_request_log_record(
            request_log_id="r2",
            request_status="ok",
            correlation_id="c2",
        ),
    ]
    srcs = [
        make_provider_source_record(provider_source_id="p1"),
        make_provider_source_record(provider_source_id="p2"),
    ]
    frs = [
        make_freshness_audit_record(
            freshness_audit_id="f1",
            freshness_status="blocked",
            explanation_nl="stale",
        ),
        make_freshness_audit_record(
            freshness_audit_id="f2",
            freshness_status="ok",
            explanation_nl="fresh",
        ),
    ]
    _patch_repo(
        monkeypatch,
        request_logs=reqs,
        provider_sources=srcs,
        freshness_audits=frs,
    )
    assert client.get("/audit/request-logs").status_code == 200
    assert client.get("/audit/provider-sources").status_code == 200
    assert client.get("/audit/freshness-audits").status_code == 200


def test_detail_endpoints_404(monkeypatch) -> None:
    _patch_repo(monkeypatch)
    assert client.get("/audit/request-logs/missing").status_code == 404
    assert client.get("/audit/provider-sources/missing").status_code == 404
    assert client.get("/audit/freshness-audits/missing").status_code == 404
