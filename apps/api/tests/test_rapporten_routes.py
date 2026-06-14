"""Tests for /rapporten endpoint (V1.2 §AX)."""

from __future__ import annotations

import json

import pytest
from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app


@pytest.fixture(autouse=True)
def _reset_storage_settings():  # type: ignore[no-untyped-def]
    original_enabled = api_settings.storage.enabled
    original_url = api_settings.storage.database_url
    original_writes = api_settings.storage.writes_enabled
    yield
    api_settings.storage.enabled = original_enabled
    api_settings.storage.database_url = original_url
    api_settings.storage.writes_enabled = original_writes


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "rapporten.sqlite")
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0076_dividend_events')"
            )
        )
    engine.dispose()
    return db_url


def _seed_action_draft(
    db_url: str,
    *,
    action_draft_id: str = "ad-1",
    status: str = "proposed",
    created_at: str = "2026-06-01T10:00:00Z",
    user_approved_at: str | None = None,
    submission_started_at: str | None = None,
    terminal_state_at: str | None = None,
) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO action_drafts ("
                "action_draft_id, decision_package_id, forecast_run_id, "
                "created_at, created_by, ibkr_account_id, conid, "
                "symbol, exchange, currency_local, side, quantity, "
                "order_type, limit_price_local, time_in_force, "
                "notional_local, notional_eur, fx_rate_at_creation, "
                "usable_cash_eur_at_creation, status, audit_trail_hash, "
                "safe_for_submission, user_approved_at, "
                "submission_started_at, terminal_state_at) VALUES "
                "(:aid, NULL, NULL, :ts, 'user', 'DU1', 'AAPL', "
                "'AAPL', 'NASDAQ', 'USD', 'BUY', 10, 'LMT', 100, 'DAY', "
                "1000, 1000, 1, 50000, :status, 'h', 0, :ua, :ss, :te)"
            ),
            {
                "aid": action_draft_id,
                "ts": created_at,
                "status": status,
                "ua": user_approved_at,
                "ss": submission_started_at,
                "te": terminal_state_at,
            },
        )
    engine.dispose()


def _seed_execution(
    db_url: str,
    *,
    exec_id: str,
    side: str,
    price: str,
    qty: str,
    fill_time: str,
    conid: str = "AAPL",
    action_draft_id: str = "ad-1",
    perm_id: int | None = None,
) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ibkr_executions ("
                "ibkr_exec_id, ibkr_perm_id, action_draft_id, "
                "account_id, conid, side, fill_price_local, "
                "fill_quantity, fill_time, commission, "
                "commission_currency, exchange) VALUES ("
                ":eid, :perm, :aid, 'DU1', :conid, :side, :price, "
                ":qty, :ft, '1', 'USD', 'NASDAQ')"
            ),
            {
                "eid": exec_id,
                "perm": perm_id if perm_id is not None else hash(exec_id) & 0x7FFFFFFF,
                "aid": action_draft_id,
                "conid": conid,
                "side": side,
                "price": price,
                "qty": qty,
                "ft": fill_time,
            },
        )
    engine.dispose()


def _seed_verdict(
    db_url: str,
    *,
    verdict_id: str,
    decision: str = "suggest",
    symbol: str = "AAPL",
    generated_at: str = "2026-06-10T09:00:00Z",
    confidence_pct: float | None = 85.0,
) -> None:
    details = (
        {"boosted_confidence_pct": str(confidence_pct)} if confidence_pct is not None else {}
    )
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO orchestrator_scoring_verdicts ("
                "verdict_id, ibkr_account_ref, symbol, ibkr_conid, "
                "forecast_id, generated_at, decision, blocking_reason, "
                "details_json, summary_nl) VALUES ("
                ":vid, 'default', :sym, 1, :fid, :ts, :dec, NULL, "
                ":dj, 'nl')"
            ),
            {
                "vid": verdict_id,
                "sym": symbol,
                "fid": f"fc-{verdict_id}",
                "ts": generated_at,
                "dec": decision,
                "dj": json.dumps(details),
            },
        )
    engine.dispose()


def _client(db_url: str) -> TestClient:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    return TestClient(app)


def _disable_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def test_returns_empty_report_when_storage_disabled() -> None:
    _disable_storage()
    body = TestClient(app).get("/rapporten/maand?year=2026&month=6").json()
    assert body["year"] == 2026
    assert body["month"] == 6
    assert body["executive_summary"]["trade_count"] == 0
    assert body["realised_trades"] == []


def test_returns_empty_report_when_no_data(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    body = _client(db).get("/rapporten/maand?year=2026&month=6").json()
    assert body["executive_summary"]["trade_count"] == 0


def test_returns_realised_trade_with_capital_gain(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_action_draft(db, action_draft_id="ad-buy", created_at="2026-05-05T10:00:00Z")
    _seed_action_draft(db, action_draft_id="ad-sell", created_at="2026-06-10T10:00:00Z")
    _seed_execution(
        db, exec_id="b1", side="BUY", price="100", qty="10",
        fill_time="2026-05-05T15:00:00Z", action_draft_id="ad-buy",
    )
    _seed_execution(
        db, exec_id="s1", side="SELL", price="110", qty="10",
        fill_time="2026-06-10T15:00:00Z", action_draft_id="ad-sell",
    )
    body = _client(db).get("/rapporten/maand?year=2026&month=6").json()
    assert body["executive_summary"]["trade_count"] == 1
    assert len(body["realised_trades"]) == 1
    assert body["realised_trades"][0]["symbol"] == "AAPL"
    assert body["realised_trades"][0]["net_local"] == "92.65"


def test_action_draft_activity_counts_month_buckets(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_action_draft(
        db, action_draft_id="ad-1", status="proposed",
        created_at="2026-06-05T10:00:00Z",
    )
    _seed_action_draft(
        db, action_draft_id="ad-2", status="user_approved",
        created_at="2026-06-06T10:00:00Z",
        user_approved_at="2026-06-07T10:00:00Z",
    )
    # Out of month — only the May created_at lands.
    _seed_action_draft(
        db, action_draft_id="ad-3", status="proposed",
        created_at="2026-05-15T10:00:00Z",
    )
    body = _client(db).get("/rapporten/maand?year=2026&month=6").json()
    a = body["action_draft_activity"]
    assert a["proposed"] == 2
    assert a["user_approved"] == 1


def test_verdict_activity_aggregates_by_decision(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_verdict(db, verdict_id="v1", symbol="A", decision="suggest")
    _seed_verdict(db, verdict_id="v2", symbol="B", decision="suggest")
    _seed_verdict(
        db, verdict_id="v3", symbol="C", decision="skip_macro_regime"
    )
    _seed_verdict(
        db, verdict_id="v4", symbol="D", decision="suggest",
        generated_at="2026-05-20T09:00:00Z",
    )
    body = _client(db).get("/rapporten/maand?year=2026&month=6").json()
    va = body["verdict_activity"]
    assert va["total"] == 3
    assert va["by_decision"]["suggest"] == 2
    assert va["by_decision"]["skip_macro_regime"] == 1


def test_confidence_distribution_buckets(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_verdict(db, verdict_id="v1", symbol="A", confidence_pct=92.0)
    _seed_verdict(db, verdict_id="v2", symbol="B", confidence_pct=82.0)
    _seed_verdict(db, verdict_id="v3", symbol="C", confidence_pct=72.0)
    _seed_verdict(db, verdict_id="v4", symbol="D", confidence_pct=55.0)
    body = _client(db).get("/rapporten/maand?year=2026&month=6").json()
    dist = body["software_performance"]["confidence_distribution_pct"]
    assert dist[">=90%"] == 25.0
    assert dist["80-90%"] == 25.0
    assert dist["70-80%"] == 25.0


def test_rejects_invalid_year(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    assert _client(db).get("/rapporten/maand?year=1999&month=6").status_code == 400


def test_rejects_invalid_month(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    assert _client(db).get("/rapporten/maand?year=2026&month=13").status_code == 400


def test_defaults_year_and_month_to_current(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    body = _client(db).get("/rapporten/maand").json()
    assert body["year"] >= 2026
    assert 1 <= body["month"] <= 12


def test_notes_warn_about_fx_and_dividends(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    body = _client(db).get("/rapporten/maand?year=2026&month=6").json()
    notes = body["notes_nl"]
    assert any("EUR" in note for note in notes)
    assert any("Dividenden" in note for note in notes)


def test_open_positions_count_reflects_latest_sync_run(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    engine = create_engine(db, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ibkr_sync_runs ("
                "sync_run_id, started_at, provider_code, "
                "provider_environment, account_mode, status, "
                "account_summary_status, positions_status, "
                "open_orders_status, executions_status, stored_at) "
                "VALUES ('run-1', :ts, 'ibkr', 'paper', 'paper', "
                "'success', 'ok', 'ok', 'ok', 'ok', :ts)"
            ),
            {"ts": "2026-06-01T10:00:00Z"},
        )
        for (snapshot_id, symbol, qty) in [
            ("p1", "AAPL", "10"),
            ("p2", "MSFT", "5"),
            ("p3", "ZERO", "0"),
        ]:
            conn.execute(
                text(
                    "INSERT INTO ibkr_position_snapshots ("
                    "snapshot_id, sync_run_id, conid, symbol, "
                    "security_type, currency, quantity, received_at, "
                    "stored_at) VALUES (:sid, 'run-1', '1', :sym, "
                    "'STK', 'USD', :qty, :ts, :ts)"
                ),
                {
                    "sid": snapshot_id,
                    "sym": symbol,
                    "qty": qty,
                    "ts": "2026-06-01T10:00:00Z",
                },
            )
    engine.dispose()
    body = _client(db).get("/rapporten/maand?year=2026&month=6").json()
    assert body["open_positions_count"] == 2  # ZERO is skipped


def test_ytd_includes_earlier_months(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_action_draft(db, action_draft_id="ad-1")
    _seed_action_draft(db, action_draft_id="ad-2")
    # March trade.
    _seed_execution(
        db, exec_id="b1", side="BUY", price="100", qty="10",
        fill_time="2026-02-01T15:00:00Z",
    )
    _seed_execution(
        db, exec_id="s1", side="SELL", price="110", qty="10",
        fill_time="2026-03-15T15:00:00Z",
    )
    # June trade.
    _seed_execution(
        db, exec_id="b2", side="BUY", price="50", qty="10", conid="MSFT",
        fill_time="2026-05-01T15:00:00Z", action_draft_id="ad-2",
    )
    _seed_execution(
        db, exec_id="s2", side="SELL", price="55", qty="10", conid="MSFT",
        fill_time="2026-06-10T15:00:00Z", action_draft_id="ad-2",
    )
    body = _client(db).get("/rapporten/maand?year=2026&month=6").json()
    # Only June's trade in net_local_by_currency.
    assert body["executive_summary"]["trade_count"] == 1
    # YTD should be > monthly net.
    monthly = float(body["income"]["net_local_by_currency"]["USD"])
    ytd = float(body["income"]["ytd_net_local_by_currency"]["USD"])
    assert ytd > monthly
