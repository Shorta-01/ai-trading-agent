"""Tests voor de operator-settings resolver (V1.2 §BD)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app
from portfolio_outlook_api.operator_settings import (
    DOCTRINE_DEFAULTS,
    _snapshot_from_strategy_blob,
    load_operator_trading_settings,
)


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
    db_path = str(tmp_path / "op.sqlite")
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
                "('0077_monthly_report_archive')"
            )
        )
    engine.dispose()
    return db_url


def _wire_storage(db_url: str) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True


def _disable_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def _seed_strategy_blob(db_url: str, blob: dict) -> None:
    """Direct SQL insert om de readiness-check te omzeilen."""

    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO trading_settings (settings_id, created_at, "
                "updated_at, version, allowed_universe_json, "
                "user_strategy_json, source, status, explanation_nl) "
                "VALUES ('default', :ts, :ts, 1, '{}', :blob, 'operator', "
                "'active', 'test')"
            ),
            {
                "ts": datetime(2026, 6, 14, tzinfo=UTC).isoformat(),
                "blob": json.dumps(blob),
            },
        )
    engine.dispose()


def _seed_profit_override(db_url: str, pct: Decimal) -> None:
    """Direct SQL insert van een runtime_config row met de §AZ override."""

    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO runtime_config (config_id, ibkr_enabled, "
                "ai_explanation_enabled, updated_at, software_paused, "
                "profit_target_net_pct) VALUES ('default', 0, 0, :ts, 0, "
                ":pct)"
            ),
            {
                "ts": datetime(2026, 6, 14, tzinfo=UTC).isoformat(),
                "pct": str(pct),
            },
        )
    engine.dispose()


# ---- _snapshot_from_strategy_blob -------------------------------


def test_snapshot_uses_doctrine_defaults_for_empty_blob() -> None:
    # Audit-correctie 2026-06-16: ``min_position_eur`` is per CLAUDE.md §3
    # **€5.000** (was foutief €25.000). ``max_sector_pct`` is 100 (= geen
    # cap) per §7.3 "Geen harde cap — sector-verdeling wordt INFO".
    snap = _snapshot_from_strategy_blob({})
    assert snap.target_net_pct == Decimal("4")
    assert snap.confidence_threshold_pct == Decimal("70")
    assert snap.min_position_eur == Decimal("5000")
    assert snap.max_sector_pct == Decimal("100")
    assert snap.earnings_block_days == 5


def test_snapshot_maps_operator_fields() -> None:
    snap = _snapshot_from_strategy_blob(
        {
            "trading_target_net_pct": "6.5",
            "trading_confidence_threshold_pct": "80",
            "trading_min_position_eur": "10000",
            "trading_max_position_eur": "50000",
            "trading_total_budget_eur": "500000",
            "trading_max_sector_pct": "20",
            "trading_earnings_block_days": 7,
        }
    )
    assert snap.target_net_pct == Decimal("6.5")
    assert snap.confidence_threshold_pct == Decimal("80")
    assert snap.min_position_eur == Decimal("10000")
    assert snap.max_position_eur == Decimal("50000")
    assert snap.total_budget_eur == Decimal("500000")
    assert snap.max_sector_pct == Decimal("20")
    assert snap.earnings_block_days == 7


def test_snapshot_falls_back_on_garbage_values() -> None:
    """Eén rotte waarde mag de hele snapshot niet kantelen."""

    snap = _snapshot_from_strategy_blob(
        {"trading_target_net_pct": "not-a-number"}
    )
    # Doctrine-default voor target, andere velden ook default.
    assert snap.target_net_pct == DOCTRINE_DEFAULTS.target_net_pct


def test_snapshot_ignores_unknown_fields() -> None:
    snap = _snapshot_from_strategy_blob({"random_field": "x", "another": 99})
    assert snap.target_net_pct == DOCTRINE_DEFAULTS.target_net_pct


# ---- load_operator_trading_settings end-to-end -------------------


def test_load_returns_doctrine_defaults_without_storage() -> None:
    _disable_storage()
    res = load_operator_trading_settings()
    assert res.source == "storage-unavailable"
    assert res.profit_target_overridden is False
    assert res.snapshot.target_net_pct == DOCTRINE_DEFAULTS.target_net_pct


def test_load_returns_doctrine_defaults_when_no_row(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _wire_storage(_seed_db(tmp_path))
    res = load_operator_trading_settings()
    assert res.source == "doctrine-default"
    assert res.snapshot.target_net_pct == DOCTRINE_DEFAULTS.target_net_pct


def test_load_returns_operator_values_when_set(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _wire_storage(db)
    _seed_strategy_blob(
        db,
        {
            "trading_target_net_pct": "5",
            "trading_min_position_eur": "10000",
            "trading_max_position_eur": "30000",
        },
    )
    res = load_operator_trading_settings()
    assert res.source == "operator"
    assert res.snapshot.target_net_pct == Decimal("5")
    assert res.snapshot.min_position_eur == Decimal("10000")
    assert res.snapshot.max_position_eur == Decimal("30000")


def test_load_applies_profit_target_override(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """§AZ overlay heeft voorrang op het strategy-blob."""

    db = _seed_db(tmp_path)
    _wire_storage(db)
    _seed_strategy_blob(
        db, {"trading_target_net_pct": "5"},
    )
    _seed_profit_override(db, Decimal("8"))
    res = load_operator_trading_settings()
    assert res.snapshot.target_net_pct == Decimal("8")
    assert res.profit_target_overridden is True


def test_profit_override_default_doesnt_flag(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Wanneer override gelijk is aan de doctrine-default 4 % wordt
    de strategy-waarde niet overschreven en de flag blijft False."""

    db = _seed_db(tmp_path)
    _wire_storage(db)
    _seed_strategy_blob(db, {"trading_target_net_pct": "6"})
    # Geen runtime_config row → override gelijk aan doctrine 4.
    res = load_operator_trading_settings()
    assert res.snapshot.target_net_pct == Decimal("6")
    assert res.profit_target_overridden is False


# ---- end-to-end via /system/status of fixed health (smoke) ------


def test_doctrine_defaults_match_orchestrator_defaults() -> None:
    """Sanity-check: onze fallback laat de orchestrator op de
    historische numbers draaien (kompatibel met bestaande tests)."""

    assert DOCTRINE_DEFAULTS.target_net_pct == Decimal("4")
    assert DOCTRINE_DEFAULTS.max_position_eur == Decimal("100000")
    assert DOCTRINE_DEFAULTS.total_budget_eur == Decimal("1000000")
    assert DOCTRINE_DEFAULTS.fat_tail_factor == Decimal("1.15")


def test_smoke_client_with_disabled_storage_returns_doctrine_default() -> None:
    """Aanroep via TestClient triggert de import-chain; geen
    regressies door circulaire imports of dergelijke."""

    _disable_storage()
    client = TestClient(app)
    # Profit-target endpoint (uit §AZ) reflecteert de doctrine-
    # default — bewijst dat de import-chain en helpers werken.
    response = client.get("/settings/profit-target")
    assert response.status_code == 200
    assert response.json()["profit_target_pct"] == "4"
