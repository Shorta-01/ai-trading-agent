"""Tests for the deterministic daily briefing builder (Slice 12)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import (
    ALERT_KIND_CRITICAL_DRAFT_EVENT,
    ALERT_KIND_DIARY_OUTCOME_CLOSED,
    ALERT_KIND_FX_STALE,
    ALERT_KIND_NEW_ACTION_DRAFT,
    ALERT_KIND_NEW_DECISION_PACKAGE,
    ALERT_KIND_NEW_SUGGESTION,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    BriefingActionDraftInput,
    BriefingCriticalEventInput,
    BriefingDecisionPackageInput,
    BriefingDiaryOutcomeInput,
    BriefingInputs,
    BriefingPositionInput,
    BriefingSuggestionInput,
    compute_daily_briefing,
)

_NOW = datetime(2025, 5, 24, 9, 0, tzinfo=UTC)
_LOOKBACK = _NOW - timedelta(hours=24)
_BEFORE_CUTOFF = _LOOKBACK - timedelta(hours=1)
_AFTER_CUTOFF = _LOOKBACK + timedelta(hours=2)


def _empty_inputs() -> BriefingInputs:
    return BriefingInputs(
        now=_NOW,
        lookback_started_at=_LOOKBACK,
        base_currency="USD",
        fx_freshness_status="fresh",
        cash_total_base_currency=Decimal("5000"),
    )


def test_empty_inputs_yield_zero_counts_and_dutch_summary() -> None:
    result = compute_daily_briefing(_empty_inputs())
    assert result.position_count == 0
    assert result.total_position_value is None
    assert result.new_suggestion_count == 0
    assert result.new_decision_package_count == 0
    assert result.new_action_draft_count == 0
    assert result.diary_outcomes_closed_count == 0
    assert result.critical_event_count == 0
    assert result.alerts == ()
    assert "Geen open posities" in result.summary_nl
    assert "Geen nieuwe suggesties" in result.summary_nl
    assert result.status == "ready"


def test_positions_count_and_total_value_are_summed() -> None:
    inputs = BriefingInputs(
        now=_NOW,
        lookback_started_at=_LOOKBACK,
        base_currency="USD",
        fx_freshness_status="fresh",
        cash_total_base_currency=Decimal("1000"),
        positions=(
            BriefingPositionInput(
                symbol="AAPL", conid="1", quantity=Decimal("5"),
                market_value_base_currency=Decimal("900"),
            ),
            BriefingPositionInput(
                symbol="MSFT", conid="2", quantity=Decimal("3"),
                market_value_base_currency=Decimal("1500"),
            ),
        ),
    )
    result = compute_daily_briefing(inputs)
    assert result.position_count == 2
    assert result.total_position_value == Decimal("2400")
    assert "2 positie" in result.summary_nl
    assert "USD 2400" in result.summary_nl


def test_only_new_suggestions_are_counted() -> None:
    inputs = BriefingInputs(
        now=_NOW,
        lookback_started_at=_LOOKBACK,
        base_currency="USD",
        fx_freshness_status="fresh",
        cash_total_base_currency=None,
        suggestions=(
            BriefingSuggestionInput(
                suggestion_id="sug-old", symbol="AAPL",
                action_label_nl="Houden", generated_at=_BEFORE_CUTOFF, status="ready",
            ),
            BriefingSuggestionInput(
                suggestion_id="sug-new", symbol="MSFT",
                action_label_nl="Kopen", generated_at=_AFTER_CUTOFF, status="ready",
            ),
        ),
    )
    result = compute_daily_briefing(inputs)
    assert result.new_suggestion_count == 1
    new_alerts = [a for a in result.alerts if a.alert_kind == ALERT_KIND_NEW_SUGGESTION]
    assert len(new_alerts) == 1
    assert new_alerts[0].reference_id == "sug-new"
    assert "MSFT" in new_alerts[0].title_nl


def test_new_decision_package_and_action_draft_alerts_are_emitted() -> None:
    inputs = BriefingInputs(
        now=_NOW,
        lookback_started_at=_LOOKBACK,
        base_currency="USD",
        fx_freshness_status="fresh",
        cash_total_base_currency=None,
        decision_packages=(
            BriefingDecisionPackageInput(
                decision_package_id="dp-1", symbol="AAPL",
                generated_at=_AFTER_CUTOFF, status="ready",
            ),
        ),
        action_drafts=(
            BriefingActionDraftInput(
                draft_id="draft-1", symbol="AAPL", action_side="BUY",
                created_at=_AFTER_CUTOFF, dry_run_status="passed",
            ),
        ),
    )
    result = compute_daily_briefing(inputs)
    assert result.new_decision_package_count == 1
    assert result.new_action_draft_count == 1
    kinds = {a.alert_kind for a in result.alerts}
    assert ALERT_KIND_NEW_DECISION_PACKAGE in kinds
    assert ALERT_KIND_NEW_ACTION_DRAFT in kinds


def test_failed_dry_run_action_draft_is_warning_severity() -> None:
    inputs = BriefingInputs(
        now=_NOW,
        lookback_started_at=_LOOKBACK,
        base_currency="USD",
        fx_freshness_status="fresh",
        cash_total_base_currency=None,
        action_drafts=(
            BriefingActionDraftInput(
                draft_id="d", symbol="AAPL", action_side="BUY",
                created_at=_AFTER_CUTOFF, dry_run_status="failed",
            ),
        ),
    )
    result = compute_daily_briefing(inputs)
    alert = next(a for a in result.alerts if a.alert_kind == ALERT_KIND_NEW_ACTION_DRAFT)
    assert alert.severity == SEVERITY_WARNING


def test_closed_diary_outcome_emits_info_alert_with_label() -> None:
    inputs = BriefingInputs(
        now=_NOW,
        lookback_started_at=_LOOKBACK,
        base_currency="USD",
        fx_freshness_status="fresh",
        cash_total_base_currency=None,
        diary_outcomes=(
            BriefingDiaryOutcomeInput(
                suggestion_id="sug-1", symbol="AAPL",
                last_evaluated_at=_AFTER_CUTOFF, outcome_label_1m="right",
            ),
        ),
    )
    result = compute_daily_briefing(inputs)
    assert result.diary_outcomes_closed_count == 1
    alert = next(a for a in result.alerts if a.alert_kind == ALERT_KIND_DIARY_OUTCOME_CLOSED)
    assert "right" in alert.title_nl
    assert alert.severity == SEVERITY_INFO


def test_diary_outcome_without_label_is_counted_but_no_alert() -> None:
    inputs = BriefingInputs(
        now=_NOW,
        lookback_started_at=_LOOKBACK,
        base_currency="USD",
        fx_freshness_status="fresh",
        cash_total_base_currency=None,
        diary_outcomes=(
            BriefingDiaryOutcomeInput(
                suggestion_id="sug-1", symbol="AAPL",
                last_evaluated_at=_AFTER_CUTOFF, outcome_label_1m=None,
            ),
        ),
    )
    result = compute_daily_briefing(inputs)
    assert result.diary_outcomes_closed_count == 1
    assert not [a for a in result.alerts if a.alert_kind == ALERT_KIND_DIARY_OUTCOME_CLOSED]


def test_critical_event_emits_critical_alert() -> None:
    inputs = BriefingInputs(
        now=_NOW,
        lookback_started_at=_LOOKBACK,
        base_currency="USD",
        fx_freshness_status="fresh",
        cash_total_base_currency=None,
        critical_events=(
            BriefingCriticalEventInput(
                event_id="evt-1", draft_id="draft-1",
                event_type="reconciled_to_filled",
                to_state="filled", occurred_at=_AFTER_CUTOFF,
            ),
        ),
    )
    result = compute_daily_briefing(inputs)
    assert result.critical_event_count == 1
    alert = next(a for a in result.alerts if a.alert_kind == ALERT_KIND_CRITICAL_DRAFT_EVENT)
    assert alert.severity == SEVERITY_CRITICAL
    assert "filled" in alert.title_nl


def test_stale_fx_status_emits_warning_alert() -> None:
    inputs = BriefingInputs(
        now=_NOW,
        lookback_started_at=_LOOKBACK,
        base_currency="USD",
        fx_freshness_status="stale",
        cash_total_base_currency=None,
    )
    result = compute_daily_briefing(inputs)
    alert = next(a for a in result.alerts if a.alert_kind == ALERT_KIND_FX_STALE)
    assert alert.severity == SEVERITY_WARNING


def test_summary_is_deterministic_for_same_inputs() -> None:
    a = compute_daily_briefing(_empty_inputs())
    b = compute_daily_briefing(_empty_inputs())
    assert a.summary_nl == b.summary_nl
    assert a.alerts == b.alerts


def test_briefing_date_is_now_date_in_utc() -> None:
    result = compute_daily_briefing(_empty_inputs())
    assert result.briefing_date == _NOW.date()


def test_items_exactly_at_cutoff_are_included() -> None:
    inputs = BriefingInputs(
        now=_NOW,
        lookback_started_at=_LOOKBACK,
        base_currency="USD",
        fx_freshness_status="fresh",
        cash_total_base_currency=None,
        suggestions=(
            BriefingSuggestionInput(
                suggestion_id="sug-at-cutoff", symbol="AAPL",
                action_label_nl="Houden", generated_at=_LOOKBACK, status="ready",
            ),
        ),
    )
    result = compute_daily_briefing(inputs)
    assert result.new_suggestion_count == 1
