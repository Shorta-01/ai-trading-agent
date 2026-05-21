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
        RequestLogRecord("r1","c1","audit","status",now,None,"ibkr","paper","sandbox","broker","market_data","list","/audit","blocked","api",0,0,0,0,0,0,False,False,False,"x"),
        RequestLogRecord("r2","c2","audit","status",now,None,"ibkr","paper","sandbox","broker","market_data","list","/audit","ok","api",0,0,0,0,0,0,True,False,False,"x"),
    ]
    provider_sources = [
        ProviderSourceRecord("p1","ibkr","broker","market_data","feed","sandbox","paper",None,None,now,now,None,None,False,False,False,"x"),
        ProviderSourceRecord("p2","ibkr","broker","market_data","feed","sandbox","paper",None,None,now,now,now,"off",False,False,False,"x"),
    ]
    freshness = [
        FreshnessAuditRecord("f1","r1","p1","market_data","snapshot","blocked","stale",now,300,999,None,None,False,False,False,"x"),
        FreshnessAuditRecord("f2","r2","p2","market_data","snapshot","ok",None,now,300,99,now,None,True,False,False,"x"),
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
    assert req["blocked_for_analysis_count"] == 1
    assert req["safe_for_analysis_count"] == 1
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
