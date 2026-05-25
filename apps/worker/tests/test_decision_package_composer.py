"""Task 132 — Decision Package composer tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trading_agent_storage import (
    AssetListingRecord,
    DecisionPackageEntry,
    ForecastEntry,
    FxRateRecord,
    IbkrPositionSnapshotRecord,
    MarketDataEodSnapshotEntry,
)

from portfolio_outlook_worker.decision_package import (
    GeblokkeerdForecastError,
    compose_decision_package,
    compute_audit_trail_hash,
    evaluate_gates,
    render_explanation,
)

_NOW = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


def _forecast(
    *,
    forecast_run_id: str = "fcst-1",
    conid: str = "ASML.AS",
    label: str = "Bekijken",
    confidence: str = "Hoog",
    block_reason: str | None = None,
    currency: str = "EUR",
    generated_at: datetime | None = None,
) -> ForecastEntry:
    ts = generated_at or _NOW
    return ForecastEntry(
        forecast_run_id=forecast_run_id,
        conid=conid,
        generated_at=ts,
        generated_by_scheduled_run_id="srun-1",
        horizon_trading_days=20,
        forecast_valid_until=ts + timedelta(days=28),
        method="historical_bootstrap_v1",
        history_window_days=252,
        history_closes_count=252,
        current_price_local=Decimal("640.000000"),
        currency_local=currency,
        p10_log_return=Decimal("-0.05"),
        p50_log_return=Decimal("0.02"),
        p90_log_return=Decimal("0.08"),
        prob_positive=Decimal("0.62"),
        prob_loss_gt_5pct=Decimal("0.12"),
        expected_volatility_annualized=Decimal("0.25"),
        confidence_level=confidence,
        label=label,
        block_reason=block_reason,
        expired_at=None,
    )


def _snapshot(
    *, as_of_date: date | None = None, currency: str = "EUR"
) -> MarketDataEodSnapshotEntry:
    return MarketDataEodSnapshotEntry(
        snapshot_id="snap-1",
        ibkr_conid="ASML.AS",
        symbol="ASML",
        exchange="AEB",
        currency_local=currency,
        as_of_date=as_of_date or _NOW.date(),
        as_of_close_ts=(
            datetime.combine(
                as_of_date or _NOW.date(),
                datetime.min.time(),
                tzinfo=UTC,
            )
            + timedelta(hours=20)
        ),
        ingested_ts=_NOW,
        open_local=Decimal("638.0"),
        high_local=Decimal("642.0"),
        low_local=Decimal("637.0"),
        close_local=Decimal("640.0"),
        adj_close_local=Decimal("640.0"),
        volume=1_000_000,
        provider="eodhd",
        provider_response_hash="abc123",
    )


def _listing() -> AssetListingRecord:
    return AssetListingRecord(
        listing_id="listing-1",
        asset_id="asset-1",
        ibkr_conid="ASML.AS",
        symbol="ASML",
        local_symbol="ASML",
        trading_class="ASML",
        security_type="STK",
        asset_class="STK",
        exchange="AEB",
        primary_exchange="AEB",
        currency="EUR",
        listing_country="NL",
        listing_status="active",
        validation_status="valid",
        validation_source="manual",
        validated_at=_NOW,
        identity_confidence="high",
        identity_source="manual",
        created_at=_NOW,
        updated_at=_NOW,
        source_reference_ids_json=None,
        audit_context_json=None,
        safe_to_use_for_market_data=True,
        safe_to_use_for_analysis=True,
        safe_to_use_for_suggestions=False,
        blocks_market_data=False,
        blocks_analysis=False,
        blocks_suggestions=False,
        explanation_nl="test",
    )


def _position(qty: Decimal = Decimal("10")) -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id="pos-1",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        security_type="STK",
        currency="EUR",
        exchange="AEB",
        primary_exchange="AEB",
        quantity=qty,
        average_cost=Decimal("620.00"),
        received_at=_NOW,
        stored_at=_NOW,
        ibkr_account_id="DU1234567",
    )


def _fx_rate(rate: str = "1.10") -> FxRateRecord:
    return FxRateRecord(
        base_currency="USD",
        quote_currency="EUR",
        as_of_date=_NOW.date(),
        rate=Decimal(rate),
        ingested_ts=_NOW,
        provider="ecb",
    )


# ---- happy path -------------------------------------------------


def test_compose_eur_native_asset_produces_full_package() -> None:
    package = compose_decision_package(
        forecast=_forecast(),
        ibkr_account_id="DU1234567",
        market_snapshot=_snapshot(),
        fx_rate=None,
        asset_listing=_listing(),
        position_snapshot=None,
        previous_package=None,
        composed_at=_NOW,
    )
    assert isinstance(package, DecisionPackageEntry)
    assert package.forecast_run_id == "fcst-1"
    assert package.conid == "ASML.AS"
    assert package.symbol == "ASML"
    assert package.exchange == "AEB"
    assert package.asset_class == "STK"
    assert package.suggested_action_label == "Bekijken"
    assert package.forecast_confidence_level == "Hoog"
    assert package.user_holds_position is False
    assert package.held_quantity is None
    assert package.held_avg_cost_local is None
    assert package.current_price_eur == Decimal("640.000000")
    # All gates pass for the happy fixture.
    assert all(g.passed for g in package.gate_outcomes)
    # Evidence references include the snapshot.
    assert any(
        ev.source_type == "market_data_snapshot"
        for ev in package.evidence_references
    )
    # Hash is non-empty SHA-256.
    assert len(package.audit_trail_hash) == 64
    # Dutch explanation contains the asset name + label + horizon.
    assert "ASML" in package.deterministic_dutch_explanation
    assert "Bekijken" in package.deterministic_dutch_explanation
    assert "20 handelsdagen" in package.deterministic_dutch_explanation
    # Safety booleans hard-False.
    assert package.safe_for_action_drafts is False
    assert package.safe_for_orders is False


def test_compose_with_held_position_marks_user_holds_true() -> None:
    package = compose_decision_package(
        forecast=_forecast(),
        ibkr_account_id="DU1234567",
        market_snapshot=_snapshot(),
        fx_rate=None,
        asset_listing=_listing(),
        position_snapshot=_position(qty=Decimal("10")),
        previous_package=None,
        composed_at=_NOW,
    )
    assert package.user_holds_position is True
    assert package.held_quantity == Decimal("10")
    assert package.held_avg_cost_local == Decimal("620.00")
    # Evidence ref includes the position snapshot.
    assert any(
        ev.source_type == "ibkr_position_snapshot"
        for ev in package.evidence_references
    )


def test_compose_with_non_eur_currency_applies_fx_rate() -> None:
    # USD-denominated asset; FX = 1.10 EUR per USD.
    package = compose_decision_package(
        forecast=_forecast(currency="USD"),
        ibkr_account_id="DU1234567",
        market_snapshot=_snapshot(currency="USD"),
        fx_rate=_fx_rate("1.10"),
        asset_listing=_listing(),
        position_snapshot=None,
        previous_package=None,
        composed_at=_NOW,
    )
    # 640 USD × 1.10 EUR/USD = 704 EUR.
    assert package.current_price_eur == Decimal("704.000000")
    # FX evidence ref present.
    assert any(
        ev.source_type == "fx_rate"
        for ev in package.evidence_references
    )


# ---- Geblokkeerd rejection --------------------------------------


def test_compose_raises_for_geblokkeerd_forecast() -> None:
    blocked = _forecast(
        label="Geblokkeerd",
        block_reason="insufficient_history",
        confidence="Laag",
    )
    with pytest.raises(GeblokkeerdForecastError, match="Geblokkeerd"):
        compose_decision_package(
            forecast=blocked,
            ibkr_account_id="DU1234567",
            market_snapshot=_snapshot(),
            fx_rate=None,
            asset_listing=_listing(),
            position_snapshot=None,
            previous_package=None,
            composed_at=_NOW,
        )


# ---- gate evaluation --------------------------------------------


def test_gate_asset_listing_resolved_fails_when_listing_is_none() -> None:
    gates = evaluate_gates(
        forecast=_forecast(),
        asset_listing=None,
        freshness_state="fresh",
        data_age_trading_days=0,
    )
    by_name = {g.gate_name: g for g in gates}
    assert by_name["asset_listing_resolved"].passed is False
    assert "Asset-listing" in by_name["asset_listing_resolved"].reason_nl


def test_gate_freshness_within_sla_fails_when_stale() -> None:
    gates = evaluate_gates(
        forecast=_forecast(),
        asset_listing=_listing(),
        freshness_state="stale",
        data_age_trading_days=10,
    )
    by_name = {g.gate_name: g for g in gates}
    assert by_name["freshness_within_sla"].passed is False
    assert "10 dagen oud" in by_name["freshness_within_sla"].reason_nl


def test_gate_confidence_at_least_medium_fails_for_laag() -> None:
    gates = evaluate_gates(
        forecast=_forecast(confidence="Laag"),
        asset_listing=_listing(),
        freshness_state="fresh",
        data_age_trading_days=0,
    )
    by_name = {g.gate_name: g for g in gates}
    assert by_name["confidence_at_least_medium"].passed is False
    assert "Laag" in by_name["confidence_at_least_medium"].reason_nl


# ---- hash idempotence + chain integrity -------------------------


def test_compose_idempotent_hash_excluding_composed_at() -> None:
    """Same forecast + same context → same audit_trail_hash.

    composed_at + decision_package_id are deliberately NOT part of the
    hash so a re-compose for the exact same logical content produces
    identical hashes — chain verifiability rests on this.
    """

    common = dict(
        forecast=_forecast(),
        ibkr_account_id="DU1234567",
        market_snapshot=_snapshot(),
        fx_rate=None,
        asset_listing=_listing(),
        position_snapshot=None,
        previous_package=None,
    )
    a = compose_decision_package(**common, composed_at=_NOW)
    b = compose_decision_package(
        **common, composed_at=_NOW + timedelta(hours=2)
    )
    assert a.audit_trail_hash == b.audit_trail_hash
    # IDs differ (UUIDs).
    assert a.decision_package_id != b.decision_package_id


def test_compose_hash_chain_links_via_previous_package_hash() -> None:
    first = compose_decision_package(
        forecast=_forecast(forecast_run_id="fcst-1"),
        ibkr_account_id="DU1234567",
        market_snapshot=_snapshot(),
        fx_rate=None,
        asset_listing=_listing(),
        position_snapshot=None,
        previous_package=None,
        composed_at=_NOW,
    )
    second = compose_decision_package(
        forecast=_forecast(forecast_run_id="fcst-2"),
        ibkr_account_id="DU1234567",
        market_snapshot=_snapshot(),
        fx_rate=None,
        asset_listing=_listing(),
        position_snapshot=None,
        previous_package=first,
        composed_at=_NOW + timedelta(days=1),
    )
    assert second.previous_package_hash == first.audit_trail_hash
    # Two distinct forecast_run_ids → distinct hashes.
    assert first.audit_trail_hash != second.audit_trail_hash


def test_compute_audit_trail_hash_is_deterministic() -> None:
    """Direct call: feeding the same dict twice yields the same hex."""

    common = dict(
        forecast_run_id="fcst-1",
        ibkr_account_id="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        asset_class="STK",
        user_holds_position=False,
        held_quantity=None,
        held_avg_cost_local=None,
        current_price_local=Decimal("640.000000"),
        current_price_eur=Decimal("640.000000"),
        as_of_market_data_ts=_NOW,
        freshness_state="fresh",
        data_age_trading_days=0,
        forecast_method="historical_bootstrap_v1",
        p10_log_return=Decimal("-0.05"),
        p50_log_return=Decimal("0.02"),
        p90_log_return=Decimal("0.08"),
        p10_price_eur=Decimal("608.769000"),
        p50_price_eur=Decimal("652.929000"),
        p90_price_eur=Decimal("693.282000"),
        prob_positive=Decimal("0.62"),
        prob_loss_gt_5pct=Decimal("0.12"),
        expected_volatility_annualized=Decimal("0.25"),
        forecast_confidence_level="Hoog",
        suggested_action_label="Bekijken",
        block_reason=None,
        gate_outcomes=evaluate_gates(
            forecast=_forecast(),
            asset_listing=_listing(),
            freshness_state="fresh",
            data_age_trading_days=0,
        ),
        evidence_references=(),
        previous_package_hash=None,
    )
    a = compute_audit_trail_hash(**common)
    b = compute_audit_trail_hash(**common)
    assert a == b
    assert len(a) == 64


# ---- Dutch explanation ------------------------------------------


def test_dutch_explanation_contains_required_elements() -> None:
    text = render_explanation(
        symbol="ASML",
        label="Kopen",
        horizon_trading_days=20,
        p10_price_eur=Decimal("608.769000"),
        p50_price_eur=Decimal("652.929000"),
        p90_price_eur=Decimal("693.282000"),
        prob_positive=Decimal("0.62"),
        prob_loss_gt_5pct=Decimal("0.12"),
        expected_volatility_annualized=Decimal("0.25"),
        confidence_level="Hoog",
        valid_until=_NOW + timedelta(days=28),
        gate_outcomes=(),
    )
    assert "ASML" in text
    assert "Kopen" in text
    assert "20 handelsdagen" in text
    assert "€608,77" in text  # p10 EUR
    assert "€652,93" in text  # p50 EUR
    assert "€693,28" in text  # p90 EUR
    assert "62%" in text  # prob_positive
    assert "12%" in text  # prob_loss_gt_5pct
    assert "Hoog" in text
    # Dutch month name (not English).
    assert "juni" in text


def test_dutch_explanation_appends_let_op_for_each_failed_gate() -> None:
    failed_gate = evaluate_gates(
        forecast=_forecast(confidence="Laag"),
        asset_listing=None,  # asset_listing_resolved will fail
        freshness_state="stale",
        data_age_trading_days=10,
    )
    text = render_explanation(
        symbol="ASML",
        label="Bekijken",
        horizon_trading_days=20,
        p10_price_eur=Decimal("608.77"),
        p50_price_eur=Decimal("652.93"),
        p90_price_eur=Decimal("693.28"),
        prob_positive=Decimal("0.5"),
        prob_loss_gt_5pct=Decimal("0.1"),
        expected_volatility_annualized=Decimal("0.25"),
        confidence_level="Laag",
        valid_until=_NOW + timedelta(days=28),
        gate_outcomes=failed_gate,
    )
    let_op_count = text.count("Let op:")
    # asset_listing_resolved + freshness_within_sla + confidence_at_least_medium
    assert let_op_count == 3
    assert "Asset-listing" in text
    assert "10 dagen oud" in text
    assert "Laag" in text


def test_dutch_explanation_rejects_geblokkeerd_label() -> None:
    with pytest.raises(ValueError, match="Geblokkeerd"):
        render_explanation(
            symbol="ASML",
            label="Geblokkeerd",
            horizon_trading_days=20,
            p10_price_eur=Decimal("608.77"),
            p50_price_eur=Decimal("652.93"),
            p90_price_eur=Decimal("693.28"),
            prob_positive=Decimal("0.5"),
            prob_loss_gt_5pct=Decimal("0.1"),
            expected_volatility_annualized=Decimal("0.25"),
            confidence_level="Hoog",
            valid_until=_NOW + timedelta(days=28),
            gate_outcomes=(),
        )
