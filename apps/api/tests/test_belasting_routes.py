"""Tests for /belasting endpoints (V1.2 §AW)."""

from __future__ import annotations

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
    db_path = str(tmp_path / "tax.sqlite")
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
                "('0074_runtime_config_software_pause')"
            )
        )
    engine.dispose()
    return db_url


def _seed_action_draft(db_url: str, *, action_draft_id: str = "ad-1") -> None:
    """ibkr_executions has a FK to action_drafts, so we need a row."""

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
                "safe_for_submission) VALUES "
                "(:aid, NULL, NULL, :ts, 'user', 'DU1', 'AAPL', "
                "'AAPL', 'NASDAQ', 'USD', 'BUY', 10, 'LMT', 100, 'DAY', "
                "1000, 1000, 1, 50000, 'proposed', 'h', 0)"
            ),
            {"aid": action_draft_id, "ts": "2026-01-10T15:00:00Z"},
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


def _client(db_url: str) -> TestClient:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    return TestClient(app)


def _disable_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


# ---- JSON endpoint -------------------------------------------------


def test_returns_empty_report_when_storage_disabled() -> None:
    _disable_storage()
    body = TestClient(app).get("/belasting/jaaroverzicht?year=2026").json()
    assert body["year"] == 2026
    assert body["realised_trades"] == []
    assert body["year_totals"]["trade_count"] == 0


def test_returns_empty_report_when_no_executions(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    body = _client(db).get("/belasting/jaaroverzicht?year=2026").json()
    assert body["realised_trades"] == []


def test_returns_realised_trades_with_fifo_match(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_action_draft(db, action_draft_id="ad-buy")
    _seed_action_draft(db, action_draft_id="ad-sell")
    _seed_execution(
        db, exec_id="b1", side="BUY", price="100", qty="10",
        fill_time="2026-01-10T15:00:00Z", action_draft_id="ad-buy",
    )
    _seed_execution(
        db, exec_id="s1", side="SELL", price="110", qty="10",
        fill_time="2026-03-15T15:00:00Z", action_draft_id="ad-sell",
    )
    body = _client(db).get("/belasting/jaaroverzicht?year=2026").json()
    trades = body["realised_trades"]
    assert len(trades) == 1
    assert trades[0]["gross_local"] == "100.00"
    # TOB on buy: 1000 * 0.0035 = 3.50; sell: 1100 * 0.0035 = 3.85.
    assert trades[0]["tob_buy_local"] == "3.50"
    assert trades[0]["tob_sell_local"] == "3.85"
    assert trades[0]["net_local"] == "92.65"
    assert trades[0]["hold_days"] == 64
    assert trades[0]["buy_action_draft_id"] == "ad-buy"
    assert trades[0]["sell_action_draft_id"] == "ad-sell"


def test_year_totals_aggregate_per_currency(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_action_draft(db, action_draft_id="ad-1")
    _seed_execution(
        db, exec_id="b1", side="BUY", price="100", qty="10",
        fill_time="2026-01-10T15:00:00Z",
    )
    _seed_execution(
        db, exec_id="s1", side="SELL", price="110", qty="10",
        fill_time="2026-03-15T15:00:00Z",
    )
    body = _client(db).get("/belasting/jaaroverzicht?year=2026").json()
    totals = body["year_totals"]
    assert totals["trade_count"] == 1
    assert "USD" in totals["gross_local_by_currency"]


def test_monthly_points_have_twelve_entries(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    body = _client(db).get("/belasting/jaaroverzicht?year=2026").json()
    assert len(body["monthly_points"]) == 12
    assert body["monthly_points"][0]["month"] == "2026-01"


def test_year_param_rejects_out_of_range(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    response = _client(db).get("/belasting/jaaroverzicht?year=1999")
    assert response.status_code == 400


def test_year_param_defaults_to_current_year_when_omitted(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    body = _client(db).get("/belasting/jaaroverzicht").json()
    assert body["year"] >= 2026


def test_response_includes_good_householder_summary(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_action_draft(db)
    _seed_execution(
        db, exec_id="b1", side="BUY", price="100", qty="10",
        fill_time="2026-01-10T15:00:00Z",
    )
    _seed_execution(
        db, exec_id="s1", side="SELL", price="110", qty="10",
        fill_time="2026-03-15T15:00:00Z",
    )
    body = _client(db).get("/belasting/jaaroverzicht?year=2026").json()
    hh = body["good_householder"]
    assert hh["uses_leverage"] is False
    assert hh["uses_shorts"] is False
    assert hh["trades_per_year"] == 1
    assert "trade" in hh["summary_nl"]


def test_response_includes_notes_about_fx_and_dividends(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    body = _client(db).get("/belasting/jaaroverzicht?year=2026").json()
    notes = body["notes_nl"]
    assert any("EUR" in note for note in notes)
    assert any("Dividenden" in note for note in notes)


def test_only_sells_in_requested_year_are_returned(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """BUY in 2025, SELL in 2026 → report for 2025 is empty,
    report for 2026 has one row."""

    db = _seed_db(tmp_path)
    _seed_action_draft(db)
    _seed_execution(
        db, exec_id="b1", side="BUY", price="100", qty="10",
        fill_time="2025-12-15T15:00:00Z",
    )
    _seed_execution(
        db, exec_id="s1", side="SELL", price="110", qty="10",
        fill_time="2026-01-20T15:00:00Z",
    )
    client = _client(db)
    body_2025 = client.get("/belasting/jaaroverzicht?year=2025").json()
    assert body_2025["realised_trades"] == []
    body_2026 = client.get("/belasting/jaaroverzicht?year=2026").json()
    assert len(body_2026["realised_trades"]) == 1


# ---- CSV endpoint --------------------------------------------------


def test_csv_returns_attachment_with_year_filename(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    response = _client(db).get("/belasting/jaaroverzicht.csv?year=2026")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'belasting-2026.csv' in response.headers["content-disposition"]


def test_csv_includes_header_row(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    response = _client(db).get("/belasting/jaaroverzicht.csv?year=2026")
    first_line = response.text.split("\r\n")[0]
    assert "symbol" in first_line
    assert "tob_aankoop" in first_line
    assert "netto" in first_line


def test_csv_includes_one_data_row_per_realised_trade(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_action_draft(db)
    _seed_execution(
        db, exec_id="b1", side="BUY", price="100", qty="10",
        fill_time="2026-01-10T15:00:00Z",
    )
    _seed_execution(
        db, exec_id="s1", side="SELL", price="110", qty="10",
        fill_time="2026-03-15T15:00:00Z",
    )
    response = _client(db).get("/belasting/jaaroverzicht.csv?year=2026")
    lines = [line for line in response.text.split("\r\n") if line.strip()]
    # 1 header + 1 data row.
    assert len(lines) == 2
    data_line = lines[1]
    assert "92.65" in data_line  # net_local


def test_csv_empty_when_no_executions(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    response = _client(db).get("/belasting/jaaroverzicht.csv?year=2026")
    lines = [line for line in response.text.split("\r\n") if line.strip()]
    # Just the header.
    assert len(lines) == 1


def test_csv_rejects_out_of_range_year(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    response = _client(db).get("/belasting/jaaroverzicht.csv?year=1999")
    assert response.status_code == 400
