"""Tests for the Decision Package sync orchestrator.

Fake repos + fake input records. We verify: happy-path bundling, the
content-hash is stable for the same inputs, incomplete-evidence-chain
skipping, persistence-error classification, and the safety contract.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetDecisionPackageRecord,
    AssetForecastRecord,
    AssetSuggestionRecord,
    FxRateSnapshotRecord,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    MarketDataLatestSnapshotRecord,
)

from portfolio_outlook_api.decision_package_sync import (
    _AssemblyContext,  # noqa: PLC2701  -- testing internal helper deliberately
    build_decision_package_record,
    serialize_decision_package_for_response,
    sync_decision_packages,
)

_NOW = datetime(2025, 5, 24, 10, 0, tzinfo=UTC)


def _position(conid: str = "1", symbol: str = "AAPL") -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id=f"pos_{conid}",
        sync_run_id="ibkr-sync-test",
        account_ref="DU",
        conid=conid,
        symbol=symbol,
        security_type="STK",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        quantity=Decimal("5"),
        average_cost=Decimal("150"),
        received_at=_NOW,
        stored_at=_NOW,
    )


def _cash(currency: str = "USD", amount: str = "5000") -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id=f"cash_{currency}",
        sync_run_id="ibkr-sync-test",
        account_ref="DU",
        base_currency=currency,
        cash=Decimal(amount),
        available_funds=Decimal(amount),
        buying_power=Decimal(amount),
        received_at=_NOW,
        stored_at=_NOW,
    )


def _market(conid: str = "1", last_price: str = "180") -> MarketDataLatestSnapshotRecord:
    return MarketDataLatestSnapshotRecord(
        snapshot_id=f"md_{conid}",
        ibkr_conid=conid,
        symbol="AAPL",
        currency="USD",
        asset_class="STK",
        exchange=None,
        primary_exchange=None,
        provider_code="eodhd",
        provider_environment="real",
        provider_account_mode="none",
        market_data_type="eod",
        requested_at=_NOW,
        received_at=_NOW,
        provider_as_of=_NOW,
        stored_at=_NOW,
        last_price=Decimal(last_price),
        bid_price=None,
        ask_price=None,
        close_price=Decimal(last_price),
        day_change_percent=None,
        status="snapshot_available",
        freshness_status="fresh",
        explanation_nl="test",
        request_log_id=None,
        provider_source_id=None,
        freshness_audit_id=None,
    )


def _forecast(conid: str = "1") -> AssetForecastRecord:
    return AssetForecastRecord(
        forecast_id=f"forecast_{conid}",
        ibkr_conid=conid,
        symbol="AAPL",
        currency="USD",
        model_code="baseline_gbm",
        model_version="v1.0.0",
        horizon_days=21,
        generated_at=_NOW,
        valid_until=_NOW,
        data_points_used=200,
        history_first_bar_date=date(2025, 1, 1),
        history_last_bar_date=date(2025, 5, 23),
        current_price=Decimal("180"),
        expected_return_pct=Decimal("1.5"),
        p10_price=Decimal("170"),
        p50_price=Decimal("182"),
        p90_price=Decimal("194"),
        prob_gain=Decimal("0.62"),
        prob_loss=Decimal("0.38"),
        prob_loss_gt_5pct=Decimal("0.1"),
        prob_loss_gt_10pct=Decimal("0.02"),
        prob_gain_gt_5pct=Decimal("0.3"),
        prob_gain_gt_10pct=Decimal("0.1"),
        expected_volatility_annual=Decimal("0.22"),
        downside_risk_score=Decimal("6.0"),
        confidence_score=Decimal("0.85"),
        direction_label="slight_up",
        direction_label_nl="Lichte stijging verwacht",
        explanation_nl="test",
        status="ready",
        blocking_reason=None,
    )


def _suggestion(
    *,
    conid: str = "1",
    forecast_id: str | None = "forecast_1",
    action_label: str = "Houden",
    status: str = "ready",
    has_position: bool = True,
) -> AssetSuggestionRecord:
    return AssetSuggestionRecord(
        suggestion_id=f"suggestion_{conid}",
        ibkr_conid=conid,
        symbol="AAPL",
        currency="USD",
        forecast_id=forecast_id,
        model_code="baseline_label_translator",
        model_version="v1.0.0",
        generated_at=_NOW,
        valid_until=_NOW,
        risk_profile="Gebalanceerd",
        has_position=has_position,
        action_label=action_label,
        action_label_nl=action_label,
        confidence_label="Hoog",
        confidence_label_nl="Hoog",
        confidence_score=Decimal("0.82"),
        rationale_nl="Test rationale",
        drivers_json=("direction_label=slight_up",),
        blockers_json=None,
        status=status,
        blocking_reason=None,
    )


def _fx(pair: str = "USD/EUR", rate: str = "0.92") -> FxRateSnapshotRecord:
    base, quote = pair.split("/")
    return FxRateSnapshotRecord(
        snapshot_id=f"fx_{pair}",
        provider="eodhd",
        source="real-time",
        base_currency=base,
        quote_currency=quote,
        pair=pair,
        rate=Decimal(rate),
        rate_type="spot",
        as_of=_NOW,
        received_at=_NOW,
        stored_at=_NOW,
        freshness_status="fresh",
        validation_status="valid",
        reason_code="ok",
        metadata_json=None,
    )


class FakeRepo:
    def __init__(self) -> None:
        self.saved: list[AssetDecisionPackageRecord] = []

    def save_asset_decision_package(self, record: AssetDecisionPackageRecord) -> object:
        self.saved.append(record)
        return None


class RaisingRepo:
    def save_asset_decision_package(self, record: AssetDecisionPackageRecord) -> object:
        raise RuntimeError("boom")


def test_happy_path_persists_one_package_with_full_evidence_chain() -> None:
    repo = FakeRepo()

    report = sync_decision_packages(
        suggestions=[_suggestion()],
        forecasts_by_id={"forecast_1": _forecast()},
        positions_by_conid={"1": _position()},
        cash_by_currency={"USD": _cash()},
        market_by_conid={"1": _market()},
        fx_by_pair={},
        base_currency="USD",
        risk_profile="Gebalanceerd",
        repo=repo,
        valid_minutes=1440,
    )

    assert report.package_total == 1
    assert report.package_persisted == 1
    assert len(repo.saved) == 1
    record = repo.saved[0]
    assert record.ibkr_conid == "1"
    assert record.suggestion_action_label == "Houden"
    assert record.forecast_id == "forecast_1"
    assert record.forecast_p50_price == Decimal("182")
    assert record.market_last_price == Decimal("180")
    assert record.position_quantity == Decimal("5")
    assert record.cash_amount == Decimal("5000")
    assert record.safe_for_action_drafts is False
    assert record.safe_for_orders is False
    assert record.safe_for_broker_submission is False
    assert "position_snapshot:pos_1" in (record.audit_links_json or ())
    assert "forecast:forecast_1" in (record.audit_links_json or ())
    assert "suggestion:suggestion_1" in (record.audit_links_json or ())
    assert any(g.startswith("market_data:") for g in (record.gate_outcomes_json or ()))


def test_content_hash_is_stable_for_the_same_inputs_and_timestamp() -> None:
    """Two records built from the same inputs at the same generated_at must
    share the same content_hash (the hash anchors the evidence, not the
    decision_package_id which is always unique)."""

    context = _AssemblyContext(
        suggestion=_suggestion(),
        forecast=_forecast(),
        position=_position(),
        cash=_cash(),
        market=_market(),
        fx=None,
        fx_required=False,
    )
    record_a = build_decision_package_record(
        context,
        risk_profile="Gebalanceerd",
        generated_at=_NOW,
        valid_until=_NOW,
    )
    record_b = build_decision_package_record(
        context,
        risk_profile="Gebalanceerd",
        generated_at=_NOW,
        valid_until=_NOW,
    )

    assert record_a.content_hash == record_b.content_hash
    assert record_a.decision_package_id != record_b.decision_package_id


def test_blocked_suggestion_is_persisted_without_requiring_full_evidence() -> None:
    """A suggestion that's already blocked / control_needed should produce a
    package even when forecast/market evidence is missing — its purpose is to
    record the gate outcome, not the upside."""

    repo = FakeRepo()
    suggestion = _suggestion(status="blocked", action_label="Geblokkeerd")

    report = sync_decision_packages(
        suggestions=[suggestion],
        forecasts_by_id={},
        positions_by_conid={"1": _position()},
        cash_by_currency={"USD": _cash()},
        market_by_conid={},
        fx_by_pair={},
        base_currency="USD",
        risk_profile="Gebalanceerd",
        repo=repo,
        valid_minutes=1440,
    )

    assert report.package_persisted == 1
    assert repo.saved[0].suggestion_status == "blocked"
    assert repo.saved[0].status == "blocked"


def test_ready_suggestion_without_forecast_is_skipped() -> None:
    repo = FakeRepo()
    suggestion = _suggestion(forecast_id="not-in-map")

    report = sync_decision_packages(
        suggestions=[suggestion],
        forecasts_by_id={},  # forecast missing
        positions_by_conid={"1": _position()},
        cash_by_currency={"USD": _cash()},
        market_by_conid={"1": _market()},
        fx_by_pair={},
        base_currency="USD",
        risk_profile="Gebalanceerd",
        repo=repo,
        valid_minutes=1440,
    )

    assert report.package_persisted == 0
    assert report.package_skipped_missing_inputs == 1
    assert any(f["reason"] == "incomplete_evidence_chain" for f in report.failures)
    assert any(f.get("missing_forecast") == "true" for f in report.failures)


def test_ready_suggestion_without_market_snapshot_is_skipped() -> None:
    repo = FakeRepo()

    report = sync_decision_packages(
        suggestions=[_suggestion()],
        forecasts_by_id={"forecast_1": _forecast()},
        positions_by_conid={"1": _position()},
        cash_by_currency={"USD": _cash()},
        market_by_conid={},  # market missing
        fx_by_pair={},
        base_currency="USD",
        risk_profile="Gebalanceerd",
        repo=repo,
        valid_minutes=1440,
    )

    assert report.package_persisted == 0
    assert report.package_skipped_missing_inputs == 1
    assert any(f.get("missing_market_snapshot") == "true" for f in report.failures)


def test_fx_evidence_is_bundled_when_base_currency_differs() -> None:
    repo = FakeRepo()
    eur_suggestion = _suggestion()
    eur_suggestion_obj = AssetSuggestionRecord(
        suggestion_id=eur_suggestion.suggestion_id,
        ibkr_conid=eur_suggestion.ibkr_conid,
        symbol="ASML",
        currency="EUR",
        forecast_id=eur_suggestion.forecast_id,
        model_code=eur_suggestion.model_code,
        model_version=eur_suggestion.model_version,
        generated_at=eur_suggestion.generated_at,
        valid_until=eur_suggestion.valid_until,
        risk_profile=eur_suggestion.risk_profile,
        has_position=eur_suggestion.has_position,
        action_label=eur_suggestion.action_label,
        action_label_nl=eur_suggestion.action_label_nl,
        confidence_label=eur_suggestion.confidence_label,
        confidence_label_nl=eur_suggestion.confidence_label_nl,
        confidence_score=eur_suggestion.confidence_score,
        rationale_nl=eur_suggestion.rationale_nl,
        drivers_json=eur_suggestion.drivers_json,
        blockers_json=eur_suggestion.blockers_json,
        status=eur_suggestion.status,
        blocking_reason=eur_suggestion.blocking_reason,
    )

    report = sync_decision_packages(
        suggestions=[eur_suggestion_obj],
        forecasts_by_id={"forecast_1": _forecast()},
        positions_by_conid={"1": _position()},
        cash_by_currency={"USD": _cash()},
        market_by_conid={"1": _market()},
        fx_by_pair={"EUR/USD": _fx("EUR/USD", "1.08")},
        base_currency="USD",
        risk_profile="Gebalanceerd",
        repo=repo,
        valid_minutes=1440,
    )

    assert report.package_persisted == 1
    record = repo.saved[0]
    assert record.fx_pair == "EUR/USD"
    assert record.fx_rate == Decimal("1.08")
    assert record.fx_freshness_status == "fresh"


def test_persistence_failure_is_classified_as_failed() -> None:
    report = sync_decision_packages(
        suggestions=[_suggestion()],
        forecasts_by_id={"forecast_1": _forecast()},
        positions_by_conid={"1": _position()},
        cash_by_currency={"USD": _cash()},
        market_by_conid={"1": _market()},
        fx_by_pair={},
        base_currency="USD",
        risk_profile="Gebalanceerd",
        repo=RaisingRepo(),
        valid_minutes=1440,
    )

    assert report.package_persisted == 0
    assert report.package_failed == 1
    assert any(f["reason"] == "persistence_error" for f in report.failures)


def test_serializer_renders_decimals_as_strings_and_keeps_safety_flags_false() -> None:
    repo = FakeRepo()
    sync_decision_packages(
        suggestions=[_suggestion()],
        forecasts_by_id={"forecast_1": _forecast()},
        positions_by_conid={"1": _position()},
        cash_by_currency={"USD": _cash()},
        market_by_conid={"1": _market()},
        fx_by_pair={},
        base_currency="USD",
        risk_profile="Gebalanceerd",
        repo=repo,
        valid_minutes=1440,
    )
    rendered = serialize_decision_package_for_response(repo.saved[0])
    for key in (
        "forecast_p10_price",
        "forecast_p50_price",
        "forecast_p90_price",
        "market_last_price",
        "position_quantity",
        "cash_amount",
        "forecast_prob_gain",
    ):
        assert isinstance(rendered[key], str)
    assert rendered["safe_for_action_drafts"] is False
    assert rendered["safe_for_orders"] is False
    assert rendered["safe_for_broker_submission"] is False
    assert isinstance(rendered["audit_links"], list)
    assert isinstance(rendered["gate_outcomes"], list)
