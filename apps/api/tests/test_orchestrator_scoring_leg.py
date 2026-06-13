"""Tests for the real orchestrator-scoring morning-chain leg (V1.2 §AB)."""

from __future__ import annotations

import os

from ai_trading_agent_storage.metadata import (
    metadata,
    orchestrator_scoring_verdicts,
)
from sqlalchemy import create_engine, select, text

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.morning_chain import (
    LEG_ORCHESTRATOR_SCORING,
    LEG_STATUS_FAILED,
    LEG_STATUS_SKIPPED,
    LEG_STATUS_SUCCEEDED,
)
from portfolio_outlook_api.orchestrator_scoring_leg import (
    build_real_orchestrator_scoring_leg,
)


def _seed_db(path: str) -> str:
    db_url = f"sqlite:///{path}"
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


def _seed_forecast(
    db_url: str,
    *,
    symbol: str = "AAPL",
    conid: str = "265598",
    forecast_id: str | None = None,
) -> None:
    engine = create_engine(db_url, future=True)
    fc_id = forecast_id or f"fc-{symbol}"
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO asset_forecasts ("
                "forecast_id, ibkr_conid, symbol, currency, model_code, "
                "model_version, horizon_days, generated_at, valid_until, "
                "data_points_used, history_first_bar_date, history_last_bar_date, "
                "current_price, expected_return_pct, p10_price, p50_price, "
                "p90_price, prob_gain, prob_loss, prob_loss_gt_5pct, "
                "prob_loss_gt_10pct, prob_gain_gt_5pct, prob_gain_gt_10pct, "
                "expected_volatility_annual, downside_risk_score, "
                "confidence_score, direction_label, direction_label_nl, "
                "explanation_nl, status, blocking_reason, safe_for_analysis, "
                "safe_for_suggestions, safe_for_action_drafts) "
                "VALUES (:fid, :conid, :sym, 'USD', 'baseline_gbm', 'v1.0.0', "
                "126, '2026-06-12 09:00:00+00', '2026-12-12 09:00:00+00', "
                "200, '2025-01-01', '2026-06-12', '100', '15', '90', '115', '140', "
                "'0.75', '0.25', '0.10', '0.05', '0.65', '0.45', '20', '0.30', "
                "'0.85', 'slight_up', 'slight_up_nl', 'test', 'ready', NULL, "
                "0, 0, 0)"
            ),
            {"fid": fc_id, "conid": conid, "sym": symbol},
        )
    engine.dispose()


def _settings(*, db_url: str, enabled: bool = True) -> Settings:
    s = Settings()
    s.storage.enabled = True
    s.storage.database_url = db_url
    s.storage.writes_enabled = True
    s.orchestrator_scoring_enabled = enabled
    return s


# ---- skip paths ------------------------------------------------------


def test_leg_skipped_when_flag_off(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "db.sqlite")
    db_url = _seed_db(db_path)
    leg = build_real_orchestrator_scoring_leg(
        _settings(db_url=db_url, enabled=False)
    )
    outcome = leg()
    assert outcome.leg_name == LEG_ORCHESTRATOR_SCORING
    assert outcome.status == LEG_STATUS_SKIPPED
    assert "staat uit" in outcome.detail_nl


def test_leg_skipped_when_storage_disabled(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "db.sqlite")
    db_url = _seed_db(db_path)
    s = _settings(db_url=db_url, enabled=True)
    s.storage.enabled = False
    leg = build_real_orchestrator_scoring_leg(s)
    outcome = leg()
    assert outcome.status == LEG_STATUS_SKIPPED
    assert "opslag is uitgeschakeld" in outcome.detail_nl.lower()


def test_leg_succeeds_with_no_forecasts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "db.sqlite")
    db_url = _seed_db(db_path)
    leg = build_real_orchestrator_scoring_leg(_settings(db_url=db_url))
    outcome = leg()
    assert outcome.status == LEG_STATUS_SUCCEEDED
    assert "geen forecasts" in outcome.detail_nl.lower()


# ---- happy path ------------------------------------------------------


def test_leg_scores_forecasts_and_persists_verdicts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "db.sqlite")
    db_url = _seed_db(db_path)
    _seed_forecast(db_url, symbol="AAPL", conid="265598")
    _seed_forecast(db_url, symbol="MSFT", conid="272093")
    leg = build_real_orchestrator_scoring_leg(_settings(db_url=db_url))
    outcome = leg()
    assert outcome.status == LEG_STATUS_SUCCEEDED
    assert "2 kandidaten" in outcome.detail_nl
    # Verdicts persisted.
    engine = create_engine(db_url, future=True)
    with engine.connect() as conn:
        rows = conn.execute(select(orchestrator_scoring_verdicts)).mappings().all()
    engine.dispose()
    assert len(rows) == 2
    symbols = {row["symbol"] for row in rows}
    assert symbols == {"AAPL", "MSFT"}


def test_leg_detail_reports_counts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "db.sqlite")
    db_url = _seed_db(db_path)
    _seed_forecast(db_url)
    leg = build_real_orchestrator_scoring_leg(_settings(db_url=db_url))
    outcome = leg()
    assert "verdicts" in outcome.detail_nl
    assert "mislukt" in outcome.detail_nl
    assert "overgeslagen" in outcome.detail_nl


def _seed_fundamentals_snapshot(
    db_url: str,
    *,
    eodhd_symbol: str,
    symbol: str,
    sector: str,
    market_cap_eur: str,
) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO asset_fundamentals_snapshots ("
                "snapshot_id, ibkr_conid, eodhd_symbol, symbol, sector, "
                "currency, market_cap, pe_ratio, pb_ratio, ev_ebitda, "
                "roic_pct, gross_margin_pct, dividend_yield_pct, "
                "return_6m_pct, return_12m_pct, raw_payload_hash, "
                "provider_code, fetched_at, stored_at, safe_for_orders, "
                "safe_for_action_drafts) VALUES ("
                ":sid, '1', :esym, :sym, :sec, 'USD', :mcap, NULL, NULL, "
                "NULL, NULL, NULL, NULL, NULL, NULL, 'h', 'eodhd', "
                "'2026-06-12 06:00:00+00', '2026-06-12 06:00:00+00', 0, 0)"
            ),
            {
                "sid": f"snap-{symbol}",
                "esym": eodhd_symbol,
                "sym": symbol,
                "sec": sector,
                "mcap": market_cap_eur,
            },
        )
    engine.dispose()


def test_leg_uses_real_fundamentals_when_storage_has_them(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """V1.2 §AM — when ``asset_fundamentals_snapshots`` has a row
    for the forecast symbol the orchestrator candidate provider
    uses the real sector + market-cap instead of the synthetic
    fallback. We can prove that indirectly: an extreme sector
    label flows into the verdict's ``details_json`` because the
    sector-concentration gate echoes it."""

    db_path = str(tmp_path / "db.sqlite")
    db_url = _seed_db(db_path)
    _seed_forecast(db_url, symbol="AAPL", conid="265598")
    _seed_fundamentals_snapshot(
        db_url,
        eodhd_symbol="AAPL.US",
        symbol="AAPL",
        sector="healthcare",
        market_cap_eur="50000000000",
    )
    leg = build_real_orchestrator_scoring_leg(_settings(db_url=db_url))
    outcome = leg()
    assert outcome.status == LEG_STATUS_SUCCEEDED
    engine = create_engine(db_url, future=True)
    with engine.connect() as conn:
        rows = conn.execute(select(orchestrator_scoring_verdicts)).mappings().all()
    engine.dispose()
    assert len(rows) == 1
    details = rows[0]["details_json"]
    # ``details_json`` is JSON-stringified on SQLite.
    import json as _json

    parsed = _json.loads(details) if isinstance(details, str) else details
    # The sector + market-cap appear in the diagnostics payload.
    blob = _json.dumps(parsed).lower()
    assert "healthcare" in blob or "50000000000" in blob


# ---- failure path ----------------------------------------------------


def test_leg_returns_failed_on_internal_exception(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # Point storage at a path that doesn't exist to force a connection
    # error in checked_connection.
    db_url = "sqlite:///" + os.path.join(
        str(tmp_path), "nonexistent_dir", "x.sqlite"
    )
    s = Settings()
    s.storage.enabled = True
    s.storage.database_url = db_url
    s.storage.writes_enabled = True
    s.orchestrator_scoring_enabled = True
    leg = build_real_orchestrator_scoring_leg(s)
    outcome = leg()
    assert outcome.status == LEG_STATUS_FAILED
    assert outcome.failure_code == "orchestrator_scoring_failed"
