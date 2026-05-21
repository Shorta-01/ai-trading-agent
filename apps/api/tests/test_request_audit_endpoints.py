from datetime import UTC, datetime

from ai_trading_agent_storage import RequestLogRecord
from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app

client = TestClient(app)


def _assert_boundary(text: str) -> None:
    t = text.lower()
    assert "read-only" in t
    assert "geen runtime-fetch" in t
    assert "geen suggesties" in t
    assert "geen orders" in t


class _Read:
    def __init__(self, record: object | None) -> None:
        self.found = record is not None
        self.record = record


class _List:
    def __init__(self, records: list[object]) -> None:
        self.records = tuple(records)


def test_list_endpoints_empty(monkeypatch) -> None:
    class Repo:
        def list_request_logs(self):
            return _List([])

        def list_provider_sources(self):
            return _List([])

        def list_freshness_audits(self):
            return _List([])

    monkeypatch.setattr(
        "portfolio_outlook_api.request_audit._with_repository", lambda op: op(Repo())
    )
    for path in ["/audit/request-logs", "/audit/provider-sources", "/audit/freshness-audits"]:
        res = client.get(path)
        assert res.status_code == 200
        payload = res.json()
        assert payload["items"] == []
        _assert_boundary(payload["help_nl"])


def test_detail_endpoints_404(monkeypatch) -> None:
    class Repo:
        def get_request_log(self, _id: str):
            return _Read(None)

        def get_provider_source(self, _id: str):
            return _Read(None)

        def get_freshness_audit(self, _id: str):
            return _Read(None)

    monkeypatch.setattr(
        "portfolio_outlook_api.request_audit._with_repository", lambda op: op(Repo())
    )
    assert client.get("/audit/request-logs/missing").status_code == 404
    assert client.get("/audit/provider-sources/missing").status_code == 404
    assert client.get("/audit/freshness-audits/missing").status_code == 404


def test_detail_returns_records_and_safety_false(monkeypatch) -> None:
    now = datetime.now(UTC)
    req = RequestLogRecord(
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
        request_status="completed_status_only",
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
    )

    class Repo:
        def get_request_log(self, _id: str):
            return _Read(req)

    monkeypatch.setattr(
        "portfolio_outlook_api.request_audit._with_repository", lambda op: op(Repo())
    )
    payload = client.get("/audit/request-logs/r1").json()
    assert payload["safe_for_analysis"] is False
    assert payload["safe_for_suggestions"] is False
    assert payload["safe_for_action_drafts"] is False
    _assert_boundary(payload["help_nl"])
