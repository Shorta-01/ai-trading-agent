"""Tests for the daily briefing orchestrator (Slice 12)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetActionDraftEventRecord,
    AssetActionDraftRecord,
    AssetDecisionPackageRecord,
    AssetSuggestionRecord,
    BriefingAlertRecord,
    DailyBriefingRecord,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    PredictionDiaryEntryRecord,
)

from portfolio_outlook_api.daily_briefing_sync import (
    generate_daily_briefing,
    serialize_briefing_for_response,
)

_NOW = datetime(2025, 5, 24, 9, 0, tzinfo=UTC)


def _position(symbol: str = "AAPL", conid: str = "1") -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id=f"pos-{conid}",
        sync_run_id="run-1",
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
        snapshot_id=f"cash-{currency}",
        sync_run_id="run-1",
        account_ref="DU",
        base_currency=currency,
        cash=Decimal(amount),
        available_funds=Decimal(amount),
        buying_power=Decimal(amount),
        received_at=_NOW,
        stored_at=_NOW,
    )


def _suggestion(generated_at: datetime) -> AssetSuggestionRecord:
    return AssetSuggestionRecord(
        suggestion_id="sug-1",
        ibkr_conid="1",
        symbol="AAPL",
        currency="USD",
        forecast_id="fc-1",
        model_code="rule_v1",
        model_version="2025-05",
        generated_at=generated_at,
        valid_until=generated_at + timedelta(days=1),
        risk_profile="Gebalanceerd",
        has_position=True,
        action_label="Houden",
        action_label_nl="Houden",
        confidence_label="Hoog",
        confidence_label_nl="Hoog",
        confidence_score=Decimal("0.75"),
        rationale_nl="r",
        drivers_json=None,
        blockers_json=None,
        status="ready",
        blocking_reason=None,
    )


def _decision_package(generated_at: datetime) -> AssetDecisionPackageRecord:
    return AssetDecisionPackageRecord(
        decision_package_id="dp-1",
        content_hash="hash-1",
        ibkr_conid="1",
        symbol="AAPL",
        currency="USD",
        risk_profile="Gebalanceerd",
        generated_at=generated_at,
        valid_until=generated_at + timedelta(days=1),
        position_snapshot_id=None,
        position_quantity=None,
        position_average_cost=None,
        cash_snapshot_id=None,
        cash_base_currency=None,
        cash_amount=None,
        market_snapshot_id=None,
        market_last_price=None,
        market_freshness_status=None,
        market_provider_code=None,
        market_provider_as_of=None,
        fx_pair=None,
        fx_rate=None,
        fx_freshness_status=None,
        forecast_id=None,
        forecast_model_code=None,
        forecast_model_version=None,
        forecast_horizon_days=None,
        forecast_p10_price=None,
        forecast_p50_price=None,
        forecast_p90_price=None,
        forecast_prob_gain=None,
        forecast_prob_loss=None,
        forecast_expected_return_pct=None,
        forecast_expected_volatility_annual=None,
        forecast_downside_risk_score=None,
        forecast_confidence_score=None,
        suggestion_id="sug-1",
        suggestion_model_code="rule_v1",
        suggestion_action_label="Houden",
        suggestion_action_label_nl="Houden",
        suggestion_confidence_label="Hoog",
        suggestion_confidence_label_nl="Hoog",
        suggestion_status="ready",
        has_position=True,
        gate_outcomes_json=None,
        evidence_links_json=None,
        audit_links_json=None,
        rationale_nl="r",
        explanation_nl="e",
        status="ready",
        blocking_reason=None,
    )


def _draft(created_at: datetime) -> AssetActionDraftRecord:
    return AssetActionDraftRecord(
        draft_id="draft-1",
        decision_package_id="dp-1",
        decision_package_content_hash="hash-1",
        ibkr_conid="1",
        symbol="AAPL",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        account_mode="paper",
        expected_account_mode="paper",
        action_side="BUY",
        order_type="LMT",
        tif="DAY",
        quantity=Decimal("5"),
        limit_price=Decimal("180"),
        estimated_order_value=Decimal("900"),
        estimated_cash_before=None,
        estimated_cash_after=None,
        estimated_position_quantity_before=Decimal("0"),
        estimated_position_quantity_after=Decimal("5"),
        estimated_position_value_after=Decimal("900"),
        estimated_portfolio_weight_after_pct=None,
        estimated_concentration_impact_pct=None,
        orderimpact_base_currency="USD",
        source_action_label="Kopen",
        source_action_label_nl="Kopen",
        status="dry_run_passed",
        dry_run_status="passed",
        dry_run_failures_json=None,
        blocking_reason=None,
        rationale_nl="r",
        explanation_nl="e",
        created_at=created_at,
        updated_at=created_at,
    )


def _diary_entry(last_evaluated_at: datetime) -> PredictionDiaryEntryRecord:
    return PredictionDiaryEntryRecord(
        entry_id="diary-1",
        suggestion_id="sug-1",
        forecast_id="fc-1",
        ibkr_conid="1",
        symbol="AAPL",
        currency="USD",
        issued_at=_NOW - timedelta(days=30),
        issued_action_label="Kopen",
        issued_action_label_nl="Kopen",
        issued_confidence_label="Hoog",
        issued_horizon_days=21,
        issued_price=Decimal("100"),
        issued_p10_price=Decimal("95"),
        issued_p50_price=Decimal("105"),
        issued_p90_price=Decimal("115"),
        issued_prob_gain=Decimal("0.6"),
        issued_prob_loss=Decimal("0.4"),
        user_decision=None,
        realized_price_1d=Decimal("100"),
        realized_price_1w=Decimal("105"),
        realized_price_1m=Decimal("112"),
        realized_return_pct_1d=None,
        realized_return_pct_1w=None,
        realized_return_pct_1m=Decimal("12.0"),
        outcome_label_1d="right",
        outcome_label_1w="right",
        outcome_label_1m="right",
        outcome_explanation_nl="ok",
        last_evaluated_at=last_evaluated_at,
        created_at=last_evaluated_at,
        updated_at=last_evaluated_at,
    )


def _critical_event(occurred_at: datetime) -> AssetActionDraftEventRecord:
    return AssetActionDraftEventRecord(
        event_id="evt-1",
        draft_id="draft-1",
        submission_id="sub-1",
        event_type="reconciled_to_filled",
        severity="critical",
        from_state="working",
        to_state="filled",
        occurred_at=occurred_at,
        acknowledged_at=None,
        rationale_nl="reconciled",
        details_json=None,
    )


class FakeBriefingRepo:
    def __init__(self, *, persistence_fails: bool = False) -> None:
        self.saved_briefings: list[DailyBriefingRecord] = []
        self.saved_alerts: list[BriefingAlertRecord] = []
        self._fail = persistence_fails

    def upsert_daily_briefing(self, record: DailyBriefingRecord) -> object:
        if self._fail:
            raise RuntimeError("storage-fail")
        self.saved_briefings.append(record)
        return None

    def save_briefing_alert(self, record: BriefingAlertRecord) -> object:
        self.saved_alerts.append(record)
        return None

    def delete_alerts_for_briefing(self, briefing_id: str) -> object:
        self.saved_alerts = [
            a for a in self.saved_alerts if a.briefing_id != briefing_id
        ]
        return None


def test_empty_storage_yields_a_persisted_briefing_with_zero_counts() -> None:
    repo = FakeBriefingRepo()
    report = generate_daily_briefing(
        positions=[],
        cash_snapshots=[],
        suggestions=[],
        decision_packages=[],
        action_drafts=[],
        diary_entries=[],
        critical_events=[],
        base_currency=None,
        fx_freshness_status=None,
        lookback_hours=24,
        repo=repo,
        now=_NOW,
    )
    assert report.status == "ready"
    assert report.briefing_id is not None
    assert report.alert_count == 0
    assert len(repo.saved_briefings) == 1
    persisted = repo.saved_briefings[0]
    assert persisted.briefing_date == _NOW.date()
    assert persisted.position_count == 0
    assert persisted.safe_for_action_drafts is False
    assert persisted.safe_for_orders is False


def test_new_suggestion_within_lookback_produces_alert() -> None:
    repo = FakeBriefingRepo()
    new_suggestion = _suggestion(_NOW - timedelta(hours=1))
    report = generate_daily_briefing(
        positions=[],
        cash_snapshots=[],
        suggestions=[new_suggestion],
        decision_packages=[],
        action_drafts=[],
        diary_entries=[],
        critical_events=[],
        base_currency="USD",
        fx_freshness_status="fresh",
        lookback_hours=24,
        repo=repo,
        now=_NOW,
    )
    assert report.alert_count == 1
    assert len(repo.saved_alerts) == 1
    assert repo.saved_alerts[0].alert_kind == "new_suggestion"
    assert repo.saved_alerts[0].briefing_id == report.briefing_id


def test_old_suggestion_outside_lookback_is_ignored() -> None:
    repo = FakeBriefingRepo()
    old_suggestion = _suggestion(_NOW - timedelta(hours=48))
    report = generate_daily_briefing(
        positions=[],
        cash_snapshots=[],
        suggestions=[old_suggestion],
        decision_packages=[],
        action_drafts=[],
        diary_entries=[],
        critical_events=[],
        base_currency="USD",
        fx_freshness_status="fresh",
        lookback_hours=24,
        repo=repo,
        now=_NOW,
    )
    assert report.alert_count == 0
    assert repo.saved_briefings[0].new_suggestion_count == 0


def test_cash_total_is_summed_and_base_currency_threaded_through() -> None:
    repo = FakeBriefingRepo()
    generate_daily_briefing(
        positions=[_position()],
        cash_snapshots=[_cash("USD", "1000"), _cash("USD", "2000")],
        suggestions=[],
        decision_packages=[],
        action_drafts=[],
        diary_entries=[],
        critical_events=[],
        base_currency="USD",
        fx_freshness_status="fresh",
        lookback_hours=24,
        repo=repo,
        now=_NOW,
    )
    persisted = repo.saved_briefings[0]
    assert persisted.cash_total == Decimal("3000")
    assert persisted.base_currency == "USD"
    assert persisted.position_count == 1


def test_critical_event_within_lookback_is_classified_as_critical_alert() -> None:
    repo = FakeBriefingRepo()
    report = generate_daily_briefing(
        positions=[],
        cash_snapshots=[],
        suggestions=[],
        decision_packages=[],
        action_drafts=[],
        diary_entries=[],
        critical_events=[_critical_event(_NOW - timedelta(hours=1))],
        base_currency=None,
        fx_freshness_status=None,
        lookback_hours=24,
        repo=repo,
        now=_NOW,
    )
    assert report.alert_count == 1
    alert = repo.saved_alerts[0]
    assert alert.alert_kind == "critical_draft_event"
    assert alert.severity == "critical"


def test_diary_entry_evaluated_within_lookback_counts_and_alerts() -> None:
    repo = FakeBriefingRepo()
    generate_daily_briefing(
        positions=[],
        cash_snapshots=[],
        suggestions=[],
        decision_packages=[],
        action_drafts=[],
        diary_entries=[_diary_entry(_NOW - timedelta(hours=1))],
        critical_events=[],
        base_currency=None,
        fx_freshness_status=None,
        lookback_hours=24,
        repo=repo,
        now=_NOW,
    )
    persisted = repo.saved_briefings[0]
    assert persisted.diary_outcomes_closed_count == 1
    kinds = {a.alert_kind for a in repo.saved_alerts}
    assert "diary_outcome_closed" in kinds


def test_decision_packages_and_drafts_within_lookback_emit_alerts() -> None:
    repo = FakeBriefingRepo()
    generate_daily_briefing(
        positions=[],
        cash_snapshots=[],
        suggestions=[],
        decision_packages=[_decision_package(_NOW - timedelta(hours=1))],
        action_drafts=[_draft(_NOW - timedelta(hours=1))],
        diary_entries=[],
        critical_events=[],
        base_currency="USD",
        fx_freshness_status="fresh",
        lookback_hours=24,
        repo=repo,
        now=_NOW,
    )
    persisted = repo.saved_briefings[0]
    assert persisted.new_decision_package_count == 1
    assert persisted.new_action_draft_count == 1
    kinds = {a.alert_kind for a in repo.saved_alerts}
    assert "new_decision_package" in kinds
    assert "new_action_draft" in kinds


def test_persistence_failure_is_classified_as_failed_without_briefing_id() -> None:
    repo = FakeBriefingRepo(persistence_fails=True)
    report = generate_daily_briefing(
        positions=[],
        cash_snapshots=[],
        suggestions=[],
        decision_packages=[],
        action_drafts=[],
        diary_entries=[],
        critical_events=[],
        base_currency=None,
        fx_freshness_status=None,
        lookback_hours=24,
        repo=repo,
        now=_NOW,
    )
    assert report.status == "failed"
    assert report.briefing_id is None
    assert "fout" in report.help_nl.lower()


def test_serializer_emits_safety_flags_false_and_alert_list() -> None:
    record = DailyBriefingRecord(
        briefing_id="brief-1",
        briefing_date=date(2025, 5, 24),
        generated_at=_NOW,
        lookback_started_at=_NOW - timedelta(hours=24),
        position_count=2,
        base_currency="USD",
        total_position_value=None,
        cash_total=Decimal("5000"),
        fx_freshness_status="fresh",
        new_suggestion_count=1,
        new_decision_package_count=0,
        new_action_draft_count=0,
        diary_outcomes_closed_count=0,
        critical_event_count=0,
        alert_count=1,
        summary_nl="test",
        help_nl="ok",
        status="ready",
        blocking_reason=None,
    )
    alert = BriefingAlertRecord(
        alert_id="alrt-1",
        briefing_id="brief-1",
        alert_kind="new_suggestion",
        severity="info",
        reference_kind="suggestion",
        reference_id="sug-1",
        title_nl="t",
        body_nl="b",
        acknowledged_at=None,
        linked_at=_NOW,
    )
    payload = serialize_briefing_for_response(record, (alert,))
    assert payload["briefing_id"] == "brief-1"
    assert payload["briefing_date"] == "2025-05-24"
    assert payload["cash_total"] == "5000"
    assert payload["total_position_value"] is None
    assert payload["safe_for_action_drafts"] is False
    assert payload["safe_for_orders"] is False
    assert len(payload["alerts"]) == 1
    assert payload["alerts"][0]["alert_id"] == "alrt-1"
