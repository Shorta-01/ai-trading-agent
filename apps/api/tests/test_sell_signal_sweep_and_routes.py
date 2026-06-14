"""Tests voor SELL-loop sweep + /sell-signals endpoints (V1.2 §BF).

Verifies dat:

1. De sweep posities + forecasts uit storage leest, beide evaluators
   aanroept en kaartjes upsert.
2. De sweep idempotent is — herhaalde calls op dezelfde state
   produceren dezelfde kaartjes (geen duplicaten).
3. Operator-dismissal sticky is tot het signaal materieel verandert.
4. CLAUDE.md §11 — de sweep is bewust pauze-agnostisch (de paused-
   flag wordt NIET gelezen door de sweep).
5. De API routes (GET /sell-signals, POST /dismiss, POST /sweep)
   over een levende SQLite-DB werken.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app
from portfolio_outlook_api.sell_signal_sweep import (
    DEFAULT_HORIZON_REVIEW_START_DAYS,
    DEFAULT_LOSS_FLOOR_PCT,
    DEFAULT_TARGET_NET_PCT,
    run_sell_signal_sweep,
)

_NOW = datetime(2026, 6, 14, 10, 30, tzinfo=UTC)
_TODAY = date(2026, 6, 14)


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
    db_path = str(tmp_path / "sell_signals.sqlite")
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(32) NOT NULL)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0079_macro_index_snapshots')"
            )
        )
        # Sweep + worker code call ``checked_connection(require_writable=
        # True)`` which validates against the readiness chain. Tests run
        # against the current head revision.
    engine.dispose()
    return db_url


def _client(db_url: str) -> TestClient:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    return TestClient(app)


def _seed_position(
    db_url: str,
    *,
    symbol: str,
    quantity: int,
    average_cost: Decimal,
    received_at: datetime,
    currency: str = "USD",
) -> None:
    """Insert one sync_run + one position row directly via SQL."""

    engine = create_engine(db_url, future=True)
    sync_run_id = f"sync_{uuid4().hex[:8]}"
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ibkr_sync_runs ("
                "sync_run_id, started_at, provider_code, "
                "provider_environment, account_mode, readonly, status, "
                "account_summary_status, positions_status, "
                "open_orders_status, executions_status, stored_at) "
                "VALUES (:id, :started_at, 'ibkr', 'paper', 'paper', "
                "1, 'succeeded', 'succeeded', 'succeeded', 'succeeded', "
                "'succeeded', :stored_at)"
            ),
            {"id": sync_run_id, "started_at": received_at, "stored_at": received_at},
        )
        conn.execute(
            text(
                "INSERT INTO ibkr_position_snapshots ("
                "snapshot_id, sync_run_id, symbol, security_type, currency, "
                "quantity, average_cost, received_at, stored_at) "
                "VALUES (:sid, :run, :sym, 'STK', :ccy, :qty, :avg, "
                ":received, :stored)"
            ),
            {
                "sid": f"snap_{uuid4().hex[:8]}",
                "run": sync_run_id,
                "sym": symbol,
                "ccy": currency,
                "qty": quantity,
                "avg": str(average_cost),
                "received": received_at,
                "stored": received_at,
            },
        )
    engine.dispose()


def _seed_forecast(
    db_url: str,
    *,
    symbol: str,
    current_price: Decimal,
    p50_price: Decimal,
    horizon_days: int = 90,
    prob_gain: Decimal = Decimal("0.6"),
    generated_at: datetime = _NOW,
) -> str:
    forecast_id = f"fc_{uuid4().hex[:8]}"
    valid_until = generated_at + timedelta(days=1)
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO asset_forecasts ("
                "forecast_id, ibkr_conid, symbol, currency, model_code, "
                "model_version, horizon_days, generated_at, valid_until, "
                "data_points_used, current_price, expected_return_pct, "
                "p10_price, p50_price, p90_price, prob_gain, prob_loss, "
                "prob_loss_gt_5pct, prob_loss_gt_10pct, prob_gain_gt_5pct, "
                "prob_gain_gt_10pct, expected_volatility_annual, "
                "downside_risk_score, confidence_score, direction_label, "
                "direction_label_nl, explanation_nl, status) "
                "VALUES (:fid, :cid, :sym, 'USD', 'gbm', 'v1', :hor, :gen, "
                ":valid, 252, :curr, '5.0', :p10, :p50, :p90, :pg, '0.3', "
                "'0.1', '0.05', '0.4', '0.2', '0.25', '0.05', '0.7', "
                "'up', 'omhoog', 'test', 'ready')"
            ),
            {
                "fid": forecast_id,
                "cid": f"conid_{symbol}",
                "sym": symbol,
                "hor": horizon_days,
                "gen": generated_at,
                "valid": valid_until,
                "curr": str(current_price),
                "p10": str(p50_price * Decimal("0.9")),
                "p50": str(p50_price),
                "p90": str(p50_price * Decimal("1.1")),
                "pg": str(prob_gain),
            },
        )
    engine.dispose()
    return forecast_id


# ----------------------------------------------------------------------
# Sweep — core behavior
# ----------------------------------------------------------------------


def test_sweep_returns_skipped_when_no_positions(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    result = run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW,
        today=lambda: _TODAY,
    )
    assert result.positions_evaluated == 0
    assert result.skipped_no_position == 1
    assert result.error_text is None


def test_sweep_skips_position_without_forecast(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="AAPL",
        quantity=100,
        average_cost=Decimal("100"),
        received_at=_NOW - timedelta(days=30),
    )
    result = run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW,
        today=lambda: _TODAY,
    )
    assert result.positions_evaluated == 1
    assert result.skipped_no_forecast == 1
    assert result.take_profit_cards_upserted == 0
    assert result.hold_review_cards_upserted == 0


def test_sweep_creates_take_profit_suggest_sell_card_at_4pct(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """+4% intraday target geraakt → action=suggest_sell."""

    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="AAPL",
        quantity=100,
        average_cost=Decimal("100"),
        received_at=_NOW - timedelta(days=30),
    )
    _seed_forecast(
        db,
        symbol="AAPL",
        current_price=Decimal("104.50"),
        p50_price=Decimal("110"),
    )
    result = run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW,
        today=lambda: _TODAY,
    )
    assert result.positions_evaluated == 1
    assert result.take_profit_cards_upserted == 1
    assert result.error_text is None

    client = _client(db)
    response = client.get("/sell-signals").json()
    cards = response["cards"]
    suggest = [c for c in cards if c["signal_kind"] == "take_profit"]
    assert len(suggest) == 1
    assert suggest[0]["action"] == "suggest_sell"
    assert "AAPL" in suggest[0]["headline_nl"]
    assert "+4" in suggest[0]["headline_nl"] or "+4," in suggest[0]["headline_nl"]


def test_sweep_creates_take_profit_hold_card_below_target(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Onder de +4% target → action=hold; geen actief kaartje in
    /sell-signals (alleen suggest_sell wordt getoond)."""

    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="AAPL",
        quantity=100,
        average_cost=Decimal("100"),
        received_at=_NOW - timedelta(days=30),
    )
    _seed_forecast(
        db,
        symbol="AAPL",
        current_price=Decimal("102"),
        p50_price=Decimal("110"),
    )
    result = run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW,
        today=lambda: _TODAY,
    )
    assert result.take_profit_cards_upserted == 1

    client = _client(db)
    cards = client.get("/sell-signals").json()["cards"]
    # No suggest_sell card visible — only hold rows in DB.
    assert all(c["action"] != "suggest_sell" for c in cards)


def test_sweep_hold_review_within_6m_window_returns_hold(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Binnen 6-maanden venster → action=hold ongeacht forecast/PL."""

    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="MSFT",
        quantity=50,
        average_cost=Decimal("400"),
        received_at=_NOW - timedelta(days=60),  # <6m
    )
    _seed_forecast(
        db,
        symbol="MSFT",
        current_price=Decimal("370"),  # -7.5% in loss
        p50_price=Decimal("390"),  # below +4% target
    )
    result = run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW,
        today=lambda: _TODAY,
    )
    assert result.hold_review_cards_upserted == 1

    client = _client(db)
    active_cards = client.get("/sell-signals").json()["cards"]
    hold_review_active = [
        c for c in active_cards if c["signal_kind"] == "hold_review"
    ]
    assert len(hold_review_active) == 0  # Within 6m → action=hold → not shown


def test_sweep_hold_review_after_6m_with_combo_trigger_suggests_sell(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Na 6+ maanden + forecast verzwakt + verlies ≥ 5%
    → action=suggest_sell."""

    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="MSFT",
        quantity=50,
        average_cost=Decimal("400"),
        received_at=_NOW - timedelta(days=240),  # >6m
    )
    _seed_forecast(
        db,
        symbol="MSFT",
        current_price=Decimal("370"),  # -7.5% loss
        p50_price=Decimal("390"),  # below +4% target → no upside
    )
    result = run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW,
        today=lambda: _TODAY,
    )
    assert result.hold_review_cards_upserted == 1

    client = _client(db)
    active_cards = client.get("/sell-signals").json()["cards"]
    hold_review_active = [
        c for c in active_cards if c["signal_kind"] == "hold_review"
    ]
    assert len(hold_review_active) == 1
    assert hold_review_active[0]["action"] == "suggest_sell"
    assert hold_review_active[0]["forecaster_above_target"] is False
    assert hold_review_active[0]["position_in_loss"] is True


def test_sweep_hold_review_after_6m_one_signal_only_returns_hold(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Na 6+m maar slechts één signaal waar → hold (combo-trigger
    vereist beide)."""

    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="MSFT",
        quantity=50,
        average_cost=Decimal("400"),
        received_at=_NOW - timedelta(days=240),
    )
    _seed_forecast(
        db,
        symbol="MSFT",
        current_price=Decimal("370"),  # -7.5% loss (signaal 2 waar)
        p50_price=Decimal("420"),  # +5% upside (signaal 1 niet waar)
    )
    result = run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW,
        today=lambda: _TODAY,
    )
    assert result.hold_review_cards_upserted == 1

    client = _client(db)
    active_cards = client.get("/sell-signals").json()["cards"]
    assert all(
        c["signal_kind"] != "hold_review" for c in active_cards
    )


def test_sweep_is_idempotent(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Twee opeenvolgende sweep-calls produceren één rij per
    (account, symbol, signal_kind) — geen duplicaten."""

    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="AAPL",
        quantity=100,
        average_cost=Decimal("100"),
        received_at=_NOW - timedelta(days=30),
    )
    _seed_forecast(
        db,
        symbol="AAPL",
        current_price=Decimal("104.50"),
        p50_price=Decimal("110"),
    )
    run_sell_signal_sweep(
        database_url=db, now=lambda: _NOW, today=lambda: _TODAY
    )
    run_sell_signal_sweep(
        database_url=db, now=lambda: _NOW, today=lambda: _TODAY
    )

    engine = create_engine(db, future=True)
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT signal_kind, COUNT(*) FROM sell_signal_cards "
                "WHERE symbol='AAPL' GROUP BY signal_kind"
            )
        ).all()
    engine.dispose()
    counts = dict(rows)
    assert counts["take_profit"] == 1
    assert counts["hold_review"] == 1


def test_sweep_deletes_cards_when_position_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Eén ronde met positie → kaartjes; volgende ronde zonder
    positie-snapshot → kaartjes verdwijnen."""

    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="AAPL",
        quantity=100,
        average_cost=Decimal("100"),
        received_at=_NOW - timedelta(days=30),
    )
    _seed_forecast(
        db,
        symbol="AAPL",
        current_price=Decimal("104.50"),
        p50_price=Decimal("110"),
    )
    run_sell_signal_sweep(
        database_url=db, now=lambda: _NOW, today=lambda: _TODAY
    )

    # Simulate dat de positie gesloten is — voeg lege sync_run toe.
    engine = create_engine(db, future=True)
    new_run_id = f"sync_{uuid4().hex[:8]}"
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ibkr_sync_runs ("
                "sync_run_id, started_at, provider_code, "
                "provider_environment, account_mode, readonly, status, "
                "account_summary_status, positions_status, "
                "open_orders_status, executions_status, stored_at) "
                "VALUES (:id, :started_at, 'ibkr', 'paper', 'paper', "
                "1, 'succeeded', 'succeeded', 'succeeded', 'succeeded', "
                "'succeeded', :stored_at)"
            ),
            {
                "id": new_run_id,
                "started_at": _NOW + timedelta(hours=1),
                "stored_at": _NOW + timedelta(hours=1),
            },
        )
    engine.dispose()

    run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW + timedelta(hours=1),
        today=lambda: _TODAY,
    )

    engine = create_engine(db, future=True)
    with engine.begin() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM sell_signal_cards")
        ).scalar()
    engine.dispose()
    assert count == 0


# ----------------------------------------------------------------------
# Dismissal stickiness (CLAUDE.md §6.3 — operator dismiss is sticky)
# ----------------------------------------------------------------------


def test_dismissal_stays_sticky_while_signal_unchanged(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="AAPL",
        quantity=100,
        average_cost=Decimal("100"),
        received_at=_NOW - timedelta(days=30),
    )
    _seed_forecast(
        db,
        symbol="AAPL",
        current_price=Decimal("105"),
        p50_price=Decimal("115"),
    )
    run_sell_signal_sweep(
        database_url=db, now=lambda: _NOW, today=lambda: _TODAY
    )
    client = _client(db)
    cards = client.get("/sell-signals").json()["cards"]
    take_profit_card = next(
        c for c in cards if c["signal_kind"] == "take_profit"
    )
    card_id = take_profit_card["card_id"]

    # Operator dismisses.
    dismiss_response = client.post(
        f"/sell-signals/{card_id}/dismiss",
        json={"reason": "ik wacht nog op verder rijzen"},
    )
    assert dismiss_response.status_code == 200
    assert dismiss_response.json()["dismissed_at"] is not None

    # Active list now empty.
    assert client.get("/sell-signals").json()["cards"] == []

    # Run sweep again — signal still suggest_sell — dismissal stays sticky.
    run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW + timedelta(minutes=30),
        today=lambda: _TODAY,
    )
    assert client.get("/sell-signals").json()["cards"] == []


def test_dismissal_clears_when_signal_transitions(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Dismissed suggest_sell → price daalt onder target → action=hold
    → daarna stijgt weer terug → action=suggest_sell → kaart komt
    terug omdat dismissal werd gewist op de hold-transitie."""

    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="AAPL",
        quantity=100,
        average_cost=Decimal("100"),
        received_at=_NOW - timedelta(days=30),
    )
    forecast_id_high = _seed_forecast(
        db,
        symbol="AAPL",
        current_price=Decimal("105"),
        p50_price=Decimal("115"),
        generated_at=_NOW,
    )
    run_sell_signal_sweep(
        database_url=db, now=lambda: _NOW, today=lambda: _TODAY
    )
    client = _client(db)
    cards = client.get("/sell-signals").json()["cards"]
    take_profit_card = next(
        c for c in cards if c["signal_kind"] == "take_profit"
    )
    card_id = take_profit_card["card_id"]
    client.post(f"/sell-signals/{card_id}/dismiss", json={"reason": "wait"})
    assert client.get("/sell-signals").json()["cards"] == []

    # Price now drops below target (transition suggest_sell → hold).
    _seed_forecast(
        db,
        symbol="AAPL",
        current_price=Decimal("101"),  # +1% < +4% target
        p50_price=Decimal("115"),
        generated_at=_NOW + timedelta(hours=2),
    )
    run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW + timedelta(hours=2),
        today=lambda: _TODAY,
    )

    # Then price recovers (transition hold → suggest_sell). Dismissal
    # was already cleared during the hold transition; the new card
    # surfaces.
    _seed_forecast(
        db,
        symbol="AAPL",
        current_price=Decimal("106"),
        p50_price=Decimal("115"),
        generated_at=_NOW + timedelta(hours=4),
    )
    run_sell_signal_sweep(
        database_url=db,
        now=lambda: _NOW + timedelta(hours=4),
        today=lambda: _TODAY,
    )

    cards_after = client.get("/sell-signals").json()["cards"]
    take_profit_active = [
        c for c in cards_after if c["signal_kind"] == "take_profit"
    ]
    assert len(take_profit_active) == 1
    assert take_profit_active[0]["action"] == "suggest_sell"
    assert take_profit_active[0]["dismissed_at"] is None
    # forecast_id had to update to the latest forecast.
    assert take_profit_active[0]["forecast_id"] != forecast_id_high


# ----------------------------------------------------------------------
# API endpoints
# ----------------------------------------------------------------------


def test_get_sell_signals_returns_empty_when_storage_disabled() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    body = TestClient(app).get("/sell-signals").json()
    assert body["cards"] == []
    assert "SELL" in body["title_nl"]


def test_dismiss_returns_404_for_unknown_card(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    client = _client(db)
    response = client.post(
        "/sell-signals/nonexistent/dismiss", json={"reason": "x"}
    )
    assert response.status_code == 404


def test_post_sweep_triggers_and_returns_counts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="AAPL",
        quantity=100,
        average_cost=Decimal("100"),
        received_at=_NOW - timedelta(days=30),
    )
    _seed_forecast(
        db,
        symbol="AAPL",
        current_price=Decimal("105"),
        p50_price=Decimal("115"),
    )
    client = _client(db)
    response = client.post("/sell-signals/sweep")
    assert response.status_code == 200
    body = response.json()
    assert body["positions_evaluated"] == 1
    assert body["take_profit_cards_upserted"] == 1
    assert body["hold_review_cards_upserted"] == 1
    assert body["error_text"] is None


# ----------------------------------------------------------------------
# CLAUDE.md §11 — pauze does NOT block the sweep
# ----------------------------------------------------------------------


def test_sweep_runs_even_when_software_paused(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """CLAUDE.md §11 — SELL-monitoring blijft draaien tijdens pauze."""

    db = _seed_db(tmp_path)
    _seed_position(
        db,
        symbol="AAPL",
        quantity=100,
        average_cost=Decimal("100"),
        received_at=_NOW - timedelta(days=30),
    )
    _seed_forecast(
        db,
        symbol="AAPL",
        current_price=Decimal("105"),
        p50_price=Decimal("115"),
    )
    client = _client(db)
    pause_response = client.post("/pauze")
    assert pause_response.json()["paused"] is True

    # Sweep should run regardless of pause flag.
    sweep_response = client.post("/sell-signals/sweep")
    assert sweep_response.status_code == 200
    assert sweep_response.json()["take_profit_cards_upserted"] == 1

    # The cards should be visible to the operator.
    cards = client.get("/sell-signals").json()["cards"]
    assert any(c["action"] == "suggest_sell" for c in cards)


def test_sweep_uses_doctrine_defaults() -> None:
    """Smoke test dat de defaults exposed zijn voor scheduler-config."""

    assert DEFAULT_TARGET_NET_PCT == Decimal("4")
    assert DEFAULT_LOSS_FLOOR_PCT == Decimal("-5")
    assert DEFAULT_HORIZON_REVIEW_START_DAYS == 180
