"""Tests for the Belgian TOB year-to-date endpoint (V1.2 §AH)."""

from __future__ import annotations

from datetime import UTC, datetime

from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "tob.sqlite")
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
                "('0071_orchestrator_scoring_verdicts')"
            )
        )
        # SQLite FK enforcement is off by default; we don't need to
        # materialise the upstream action_draft row to insert
        # executions for this read-only test.
    engine.dispose()
    return db_url


def _insert_execution(
    db_url: str,
    *,
    exec_id: str,
    side: str = "BUY",
    fill_price: str = "100",
    fill_qty: str = "10",
    currency: str = "EUR",
    fill_time: datetime = datetime(2026, 6, 12, 14, 0, tzinfo=UTC),
) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ibkr_executions ("
                "ibkr_exec_id, ibkr_perm_id, action_draft_id, account_id, "
                "conid, side, fill_price_local, fill_quantity, fill_time, "
                "commission, commission_currency, exchange) VALUES ("
                ":eid, 1, 'd1', 'DU1', '1', :side, :price, :qty, :ft, "
                "0.5, :ccy, 'NASDAQ')"
            ),
            {
                "eid": exec_id,
                "side": side,
                "price": fill_price,
                "qty": fill_qty,
                "ft": fill_time.isoformat(),
                "ccy": currency,
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


def test_tob_ytd_empty_when_storage_disabled() -> None:
    _disable_storage()
    client = TestClient(app)
    response = client.get("/tob/year-to-date?year=2026")
    assert response.status_code == 200
    body = response.json()
    assert body["executions_count"] == 0
    assert body["by_currency"] == {}
    assert body["year"] == 2026


def test_tob_ytd_empty_when_no_executions(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.get("/tob/year-to-date?year=2026")
    assert response.status_code == 200
    body = response.json()
    assert body["executions_count"] == 0
    assert "Nog geen IBKR-fills" in body["note_nl"]


def test_tob_ytd_applies_standard_stock_rate_per_currency(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    # EUR buy: 10 * 100 = 1000 → TOB 0,35% = 3,50
    _insert_execution(db_url, exec_id="e1", currency="EUR")
    # USD sell: 5 * 200 = 1000 → TOB 0,35% = 3,50
    _insert_execution(
        db_url, exec_id="e2", side="SELL", fill_price="200", fill_qty="5",
        currency="USD",
    )
    client = _client(db_url)
    response = client.get("/tob/year-to-date?year=2026")
    assert response.status_code == 200
    body = response.json()
    assert body["executions_count"] == 2
    assert body["by_currency"] == {"EUR": "3.50", "USD": "3.50"}
    assert body["by_security_class"]["standard_stock"]["EUR"] == "3.50"
    assert body["by_security_class"]["standard_stock"]["USD"] == "3.50"
    assert "standard_stock" in body["note_nl"]


def test_tob_ytd_filters_to_requested_year(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _insert_execution(
        db_url, exec_id="e1", fill_time=datetime(2025, 12, 31, 22, 0, tzinfo=UTC)
    )
    _insert_execution(
        db_url, exec_id="e2", fill_time=datetime(2026, 1, 2, 9, 0, tzinfo=UTC)
    )
    client = _client(db_url)
    body = client.get("/tob/year-to-date?year=2026").json()
    assert body["executions_count"] == 1
    assert body["by_currency"] == {"EUR": "3.50"}


def test_tob_ytd_rejects_implausible_year(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.get("/tob/year-to-date?year=1900")
    assert response.status_code == 400


def test_tob_ytd_defaults_to_current_year(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.get("/tob/year-to-date")
    assert response.status_code == 200
    assert response.json()["year"] == datetime.now(tz=UTC).year
