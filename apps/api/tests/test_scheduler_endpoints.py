"""Endpoint tests for the scheduler routes (Slice 13)."""

from __future__ import annotations

from datetime import UTC, datetime

from ai_trading_agent_storage import SchedulerRunRecord
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_NOW = datetime(2026, 6, 1, 6, 30, tzinfo=UTC)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.scheduler_enabled = False
    api_settings.ibkr_expected_environment = "paper"


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _scheduler_run() -> SchedulerRunRecord:
    return SchedulerRunRecord(
        run_id="run-1",
        job_name="daily_briefing",
        scheduled_at=_NOW,
        started_at=_NOW,
        finished_at=_NOW,
        status="succeeded",
        error_text=None,
        triggered_by="scheduler",
    )


def _fake_storage(monkeypatch, *, latest_run=None, recent_runs=None) -> None:
    class _Connection:
        connection = "fake"
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Connection()

        def __exit__(self, *_):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    class _FakeRepo:
        def get_latest_scheduler_run(self, *, job_name=None):
            if latest_run is None:
                return type("_R", (), {"found": False, "record": None})()
            return type("_R", (), {"found": True, "record": latest_run})()

        def list_scheduler_runs(self, *, limit: int = 50):
            records = tuple(recent_runs or ())[:limit]
            return type("_L", (), {"records": records})()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemySchedulerRunRepository",
        lambda *a, **k: _FakeRepo(),
    )


# ---- GET /scheduler/jobs ----------------------------------------------


def test_jobs_endpoint_reports_disabled_by_default() -> None:
    r = client.get("/scheduler/jobs")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "disabled"
    assert body["scheduler_enabled"] is False
    assert body["items"] == []
    assert body["safe_for_orders"] is False


# ---- GET /scheduler/runs/latest ---------------------------------------


def test_latest_run_returns_not_configured_without_storage() -> None:
    r = client.get("/scheduler/runs/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"


def test_latest_run_returns_not_found_when_no_runs(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch)

    r = client.get("/scheduler/runs/latest")
    body = r.json()
    assert body["status"] == "not_found"
    assert body["item"] is None


def test_latest_run_returns_record_when_present(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, latest_run=_scheduler_run())

    r = client.get("/scheduler/runs/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["item"]["run_id"] == "run-1"
    assert body["item"]["status"] == "succeeded"
    assert body["item"]["triggered_by"] == "scheduler"
    assert body["safe_for_orders"] is False


# ---- GET /scheduler/runs (recent list) --------------------------------


def test_recent_runs_returns_not_configured_without_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    r = client.get("/scheduler/runs")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["items"] == []


def test_recent_runs_returns_empty_list_when_no_runs(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, recent_runs=())

    r = client.get("/scheduler/runs")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["items"] == []


def test_recent_runs_returns_records_when_present(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, recent_runs=(_scheduler_run(),))

    r = client.get("/scheduler/runs")
    body = r.json()
    assert body["status"] == "ok"
    assert len(body["items"]) == 1
    assert body["items"][0]["run_id"] == "run-1"
    assert body["items"][0]["status"] == "succeeded"
    assert body["safe_for_orders"] is False


def test_recent_runs_bounds_limit(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, recent_runs=tuple(_scheduler_run() for _ in range(5)))

    # Operator-supplied limit gets clamped to [1, 200] but otherwise honored.
    r = client.get("/scheduler/runs?limit=3")
    body = r.json()
    assert body["limit"] == 3
    assert len(body["items"]) == 3


# ---- GET /ibkr/account/mode -------------------------------------------


def test_account_mode_endpoint_reports_paper_when_hint_is_paper_account() -> None:
    """V1.2 §BZ — mode-detectie via account-id prefix. ``DU*``/``DF*``
    prefix → paper."""

    api_settings.ibkr_account_id_hint = "DU1234567"
    r = client.get("/ibkr/account/mode")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["mode"] == "paper"
    assert body["display_label"] == "PAPER"
    assert body["safe_for_orders"] is False


def test_account_mode_endpoint_reports_live_when_hint_is_live_account() -> None:
    """V1.2 §BZ — ``U*`` prefix → live. De badge volgt het feitelijk
    geconfigureerde account, niet een static config-string."""

    api_settings.ibkr_account_id_hint = "U7654321"
    r = client.get("/ibkr/account/mode")
    body = r.json()
    assert body["mode"] == "live"
    assert body["display_label"] == "LIVE"
    # Critical assertion: live mode does NOT change the safety flags;
    # the route reports the mode, it doesn't authorize anything.
    assert body["safe_for_orders"] is False
    assert body["blocks_orders"] is True


def test_account_mode_endpoint_reports_unknown_when_hint_is_unset() -> None:
    api_settings.ibkr_account_id_hint = None
    r = client.get("/ibkr/account/mode")
    body = r.json()
    assert body["mode"] == "unknown"
    assert body["display_label"] == "UNKNOWN"
    # Storage is uit in deze test → val terug op hint (None).
    assert body["detected_source"] == "hint"


def test_account_mode_endpoint_prefers_actual_tws_account_over_stale_hint(
    monkeypatch,
) -> None:
    """V1.2 §BZ vervolg — sluit de residuele safety-hole:

    De operator configureert een paper-hint (``DU1234567``) maar
    verbindt PER ONGELUK een live-account (``U7654321``). Het audit-log
    rapporteert ``U*``. De badge MOET LIVE tonen, niet PAPER — anders
    denkt de operator paper te draaien terwijl er live geld kan
    bewegen."""

    from portfolio_outlook_api import (
        ibkr_connection_read_model as conn_module,
    )
    from portfolio_outlook_api import status_routes
    from portfolio_outlook_api.ibkr_connection_read_model import (
        IbkrConnectionStatus,
    )

    api_settings.ibkr_account_id_hint = "DU1234567"  # operator's intent

    def _fake_read(_storage, *, configured_account_id, audit_limit=200):
        # TWS daadwerkelijk verbonden met een live-account.
        return IbkrConnectionStatus(
            connected=True,
            account_mode="live",
            account_id="U7654321",
            verified_at=None,
            error_nl=None,
        )

    monkeypatch.setattr(
        status_routes, "read_connection_status", _fake_read, raising=False
    )
    # Inject ook in de read-model module zodat de lokale import in
    # de endpoint dezelfde patched function pakt.
    monkeypatch.setattr(
        conn_module, "read_connection_status", _fake_read
    )

    r = client.get("/ibkr/account/mode")
    body = r.json()

    # CRITISCH: de badge volgt het ACTUELE verbonden account, niet de hint.
    assert body["mode"] == "live"
    assert body["display_label"] == "LIVE"
    assert body["detected_source"] == "connected_session"
    # Safety flags blijven ongewijzigd — endpoint authoriseert niets.
    assert body["safe_for_orders"] is False
    assert body["blocks_orders"] is True


def test_account_mode_endpoint_falls_back_to_hint_when_no_active_session(
    monkeypatch,
) -> None:
    """Wanneer er geen actieve sessie is (status.connected=False) valt
    de detectie terug op de hint. ``detected_source`` rapporteert dat
    expliciet."""

    from portfolio_outlook_api import (
        ibkr_connection_read_model as conn_module,
    )
    from portfolio_outlook_api.ibkr_connection_read_model import (
        IbkrConnectionStatus,
    )

    api_settings.ibkr_account_id_hint = "DU1234567"

    def _fake_read(_storage, *, configured_account_id, audit_limit=200):
        # Niet verbonden → moet hint gebruiken.
        return IbkrConnectionStatus(
            connected=False,
            account_mode=None,
            account_id=None,
            verified_at=None,
            error_nl="niet verbonden",
        )

    monkeypatch.setattr(conn_module, "read_connection_status", _fake_read)

    r = client.get("/ibkr/account/mode")
    body = r.json()

    assert body["mode"] == "paper"
    assert body["display_label"] == "PAPER"
    assert body["detected_source"] == "hint"


def test_account_mode_endpoint_surfaces_hint_mismatch_for_dashboard_banner(
    monkeypatch,
) -> None:
    """V1.2 §BZ vervolg — wanneer de hint (paper) niet matcht met het
    actueel verbonden account (live), MOET de endpoint dat actief
    rapporteren via ``hint_mismatch=True`` + een NL-melding. Het
    dashboard gebruikt dat om een waarschuwingsbanner te tonen
    zonder dat de operator naar /systeemmeldingen hoeft."""

    from portfolio_outlook_api import (
        ibkr_connection_read_model as conn_module,
    )
    from portfolio_outlook_api.ibkr_connection_read_model import (
        IbkrConnectionStatus,
    )

    api_settings.ibkr_account_id_hint = "DU1234567"

    def _fake_read(_storage, *, configured_account_id, audit_limit=200):
        return IbkrConnectionStatus(
            connected=True,
            account_mode="live",
            account_id="U7654321",
            verified_at=None,
            error_nl=None,
        )

    monkeypatch.setattr(conn_module, "read_connection_status", _fake_read)

    r = client.get("/ibkr/account/mode")
    body = r.json()

    # Mode-detectie volgt het verbonden account (zie #671), maar daarnaast:
    assert body["hint_mismatch"] is True
    assert body["hint_mismatch_nl"] is not None
    # Gemaskeerde IDs zodat het dashboard ze veilig kan tonen.
    # ``mask_account_id`` houdt 2-char prefix + 4-char suffix.
    assert body["hint_account_id_masked"] == "DU•••4567"
    assert body["actual_account_id_masked"] == "U7•••4321"
    # NL-melding bevat beide gemaskeerde IDs zodat de operator ziet
    # wat config zegt en wat TWS rapporteert.
    assert "DU•••4567" in body["hint_mismatch_nl"]
    assert "U7•••4321" in body["hint_mismatch_nl"]


def test_account_mode_endpoint_no_mismatch_when_hint_matches_actual(
    monkeypatch,
) -> None:
    """Wanneer hint en actueel account hetzelfde zijn, is er geen
    mismatch — geen banner moet getoond worden."""

    from portfolio_outlook_api import (
        ibkr_connection_read_model as conn_module,
    )
    from portfolio_outlook_api.ibkr_connection_read_model import (
        IbkrConnectionStatus,
    )

    api_settings.ibkr_account_id_hint = "DU1234567"

    def _fake_read(_storage, *, configured_account_id, audit_limit=200):
        return IbkrConnectionStatus(
            connected=True,
            account_mode="paper",
            account_id="DU1234567",  # zelfde als hint
            verified_at=None,
            error_nl=None,
        )

    monkeypatch.setattr(conn_module, "read_connection_status", _fake_read)

    r = client.get("/ibkr/account/mode")
    body = r.json()

    assert body["hint_mismatch"] is False
    assert body["hint_mismatch_nl"] is None
    assert body["hint_account_id_masked"] == "DU•••4567"
    assert body["actual_account_id_masked"] == "DU•••4567"


def test_account_mode_endpoint_no_mismatch_when_no_actual_session(
    monkeypatch,
) -> None:
    """Geen actieve sessie → kan geen mismatch bestaan (we hebben
    geen actual om mee te vergelijken)."""

    from portfolio_outlook_api import (
        ibkr_connection_read_model as conn_module,
    )
    from portfolio_outlook_api.ibkr_connection_read_model import (
        IbkrConnectionStatus,
    )

    api_settings.ibkr_account_id_hint = "DU1234567"

    def _fake_read(_storage, *, configured_account_id, audit_limit=200):
        return IbkrConnectionStatus(
            connected=False,
            account_mode=None,
            account_id=None,
            verified_at=None,
            error_nl="niet verbonden",
        )

    monkeypatch.setattr(conn_module, "read_connection_status", _fake_read)

    r = client.get("/ibkr/account/mode")
    body = r.json()

    assert body["hint_mismatch"] is False
    assert body["hint_mismatch_nl"] is None
    assert body["hint_account_id_masked"] == "DU•••4567"
    assert body["actual_account_id_masked"] is None


# ---- POST /scheduler/runs/morning-chain (Slice 21) --------------------


def _fake_writable_storage(monkeypatch, *, saved: list, updated: list) -> None:
    class _Connection:
        connection = "fake"
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Connection()

        def __exit__(self, *_):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    class _FakeRepo:
        def save_scheduler_run(self, record):
            saved.append(record)

        def update_scheduler_run(self, record):
            updated.append(record)

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemySchedulerRunRepository",
        lambda *a, **k: _FakeRepo(),
    )


def test_morning_chain_route_blocks_when_scheduler_disabled() -> None:
    r = client.post("/scheduler/runs/morning-chain")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["blocking_reason"] == "scheduler_disabled"
    assert body["safe_for_orders"] is False


def test_morning_chain_route_blocks_when_storage_not_writable() -> None:
    api_settings.scheduler_enabled = True
    r = client.post("/scheduler/runs/morning-chain")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["blocking_reason"] == "storage_not_writable"


def test_morning_chain_route_runs_and_persists_audit_row(monkeypatch) -> None:
    api_settings.scheduler_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    saved: list = []
    updated: list = []
    _fake_writable_storage(monkeypatch, saved=saved, updated=updated)

    # All per-leg flags off → every leg returns "skipped" → chain succeeds.
    r = client.post("/scheduler/runs/morning-chain")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "succeeded"
    assert body["result"]["status"] == "succeeded"
    assert body["result"]["failed_leg"] is None
    assert len(body["result"]["legs"]) == 8
    assert body["safe_for_orders"] is False

    # One audit row saved (running), one updated (succeeded).
    assert len(saved) == 1
    assert saved[0].status == "running"
    assert saved[0].triggered_by == "manual"
    assert len(updated) == 1
    assert updated[0].status == "succeeded"
    assert updated[0].error_text is None


def test_morning_chain_route_reports_failed_leg_in_audit_row(monkeypatch) -> None:
    api_settings.scheduler_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    saved: list = []
    updated: list = []
    _fake_writable_storage(monkeypatch, saved=saved, updated=updated)

    # Replace the wiring helper with one that returns failing legs.
    # V1.2 §BG — ``run_morning_chain_manually`` calls
    # :func:`build_morning_chain_legs_with_real_overrides` now (i.p.v.
    # rechtstreeks ``build_default_morning_chain_legs``) zodat de
    # real EODHD-backed earnings leg ook in het HTTP-trigger pad
    # geïnjecteerd wordt.
    from portfolio_outlook_api import morning_chain as mc
    from portfolio_outlook_api import morning_chain_legs_wiring as wiring

    def _failing_legs(_settings):
        return (
            lambda: mc.MorningChainLegOutcome(
                leg_name=mc.LEG_MARKET_DATA_SYNC,
                status=mc.LEG_STATUS_SUCCEEDED,
                failure_code=None,
                detail_nl="ok",
            ),
            lambda: mc.MorningChainLegOutcome(
                leg_name=mc.LEG_FORECAST_SYNC,
                status=mc.LEG_STATUS_FAILED,
                failure_code="forecast_kapot",
                detail_nl="forecast kapot",
            ),
        )

    monkeypatch.setattr(
        wiring, "build_morning_chain_legs_with_real_overrides", _failing_legs
    )

    r = client.post("/scheduler/runs/morning-chain")
    body = r.json()
    assert body["status"] == "failed"
    assert body["result"]["failed_leg"] == "forecast_sync"
    assert body["result"]["failure_code"] == "forecast_kapot"

    # Audit row updated to failed with the failure summary.
    assert updated[0].status == "failed"
    assert updated[0].error_text is not None
    assert "forecast_sync" in updated[0].error_text
    assert "forecast_kapot" in updated[0].error_text
