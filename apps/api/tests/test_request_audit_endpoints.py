from datetime import UTC, datetime

from ai_trading_agent_storage import FreshnessAuditRecord, ProviderSourceRecord, RequestLogRecord
from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app

client = TestClient(app)


def _assert_boundary(text: str) -> None:
    t = text.lower()
    assert "read-only" in t
    assert "geen runtime-fetch" in t
    assert "geen suggesties" in t
    assert "geen orders" in t
    assert "geen analysevrijgave" in t


class _Read:
    def __init__(self, record: object | None) -> None:
        self.found = record is not None
        self.record = record


class _List:
    def __init__(self, records: list[object]) -> None:
        self.records = tuple(records)


def test_list_endpoints_empty(monkeypatch) -> None:
    class Repo:
        def list_request_logs(self): return _List([])
        def list_provider_sources(self): return _List([])
        def list_freshness_audits(self): return _List([])

    monkeypatch.setattr(
        "portfolio_outlook_api.request_audit._with_repository",
        lambda op: op(Repo()),
    )
    for path in ["/audit/request-logs", "/audit/provider-sources", "/audit/freshness-audits"]:
        payload = client.get(path).json()
        assert payload["items"] == []
        assert payload["total_count"] == 0
        _assert_boundary(payload["help_nl"])


def test_summary_counts_populated(monkeypatch) -> None:
    now = datetime.now(UTC)
    request_logs = [
        RequestLogRecord(
            request_log_id="r1",
            correlation_id="c1",
            request_family="audit",
            request_purpose="status",
            created_at=now,
            completed_at=None,
            provider_code="ibkr",
            provider_account_mode="paper",
            provider_environment="sandbox",
            source_type="broker",
            data_domain="market_data",
            request_kind="list",
            request_target="/audit",
            request_status="blocked",
            initiated_by="api",
            pacing_weight=0,
            provider_request_budget_remaining=0,
            retry_count=0,
            received_record_count=0,
            stored_record_count=0,
            rejected_record_count=0,
            safe_for_analysis=False,
            safe_for_suggestions=False,
            safe_for_action_drafts=False,
            explanation_nl="x",
        ),
        RequestLogRecord(
            request_log_id="r2",
            correlation_id="c2",
            request_family="audit",
            request_purpose="status",
            created_at=now,
            completed_at=None,
            provider_code="ibkr",
            provider_account_mode="paper",
            provider_environment="sandbox",
            source_type="broker",
            data_domain="market_data",
            request_kind="list",
            request_target="/audit",
            request_status="ok",
            initiated_by="api",
            pacing_weight=0,
            provider_request_budget_remaining=0,
            retry_count=0,
            received_record_count=0,
            stored_record_count=0,
            rejected_record_count=0,
            safe_for_analysis=False,
            safe_for_suggestions=False,
            safe_for_action_drafts=False,
            explanation_nl="x",
        ),
    ]
    provider_sources = [
        ProviderSourceRecord(
            provider_source_id="p1",
            provider_code="ibkr",
            provider_kind="broker",
            data_domain="market_data",
            source_type="feed",
            provider_environment="sandbox",
            provider_account_mode="paper",
            source_effective_from=None,
            source_effective_to=None,
            created_at=now,
            updated_at=now,
            explanation_nl="x",
        ),
        ProviderSourceRecord(
            provider_source_id="p2",
            provider_code="ibkr",
            provider_kind="broker",
            data_domain="market_data",
            source_type="feed",
            provider_environment="sandbox",
            provider_account_mode="paper",
            source_effective_from=None,
            source_effective_to=now,
            created_at=now,
            updated_at=now,
            explanation_nl="off",
        ),
    ]
    freshness = [
        FreshnessAuditRecord(
            freshness_audit_id="f1",
            evaluated_at=now,
            data_domain="market_data",
            freshness_policy_code="snapshot",
            freshness_status="blocked",
            snapshot_as_of=now,
            stale_after=now,
            expires_at=None,
            age_seconds=999,
            freshness_window_seconds=300,
            safe_for_analysis=False,
            safe_for_suggestions=False,
            safe_for_action_drafts=False,
            explanation_nl="stale",
        ),
        FreshnessAuditRecord(
            freshness_audit_id="f2",
            evaluated_at=now,
            data_domain="market_data",
            freshness_policy_code="snapshot",
            freshness_status="ok",
            snapshot_as_of=now,
            stale_after=None,
            expires_at=None,
            age_seconds=99,
            freshness_window_seconds=300,
            safe_for_analysis=False,
            safe_for_suggestions=False,
            safe_for_action_drafts=False,
            explanation_nl="fresh",
        ),
    ]

    class Repo:
        def list_request_logs(self): return _List(request_logs)
        def list_provider_sources(self): return _List(provider_sources)
        def list_freshness_audits(self): return _List(freshness)

    monkeypatch.setattr(
        "portfolio_outlook_api.request_audit._with_repository",
        lambda op: op(Repo()),
    )
    req = client.get("/audit/request-logs").json()
    assert req["total_count"] == 2
    assert req["safe_for_analysis_count"] == 0
    assert req["safe_for_suggestions_count"] == 0
    assert req["safe_for_action_drafts_count"] == 0
    assert req["blocked_for_analysis_count"] == req["total_count"]
    assert req["blocked_for_suggestions_count"] == req["total_count"]
    assert req["blocked_for_action_drafts_count"] == req["total_count"]
    assert req["request_status_counts"]["blocked"] == 1
    src = client.get("/audit/provider-sources").json()
    assert src["disabled_count"] == 1
    assert src["active_metadata_count"] == 1
    fr = client.get("/audit/freshness-audits").json()
    assert fr["freshness_status_counts"]["blocked"] == 1
    assert fr["reason_code_counts"]["stale"] == 1


def test_detail_endpoints_404(monkeypatch) -> None:
    class Repo:
        def get_request_log(self, _id: str): return _Read(None)
        def get_provider_source(self, _id: str): return _Read(None)
        def get_freshness_audit(self, _id: str): return _Read(None)

    monkeypatch.setattr(
        "portfolio_outlook_api.request_audit._with_repository",
        lambda op: op(Repo()),
    )
    assert client.get("/audit/request-logs/missing").status_code == 404
