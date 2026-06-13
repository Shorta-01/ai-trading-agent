"""Pure-Python tests for the monthly report engine (V1.2 §AX)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_outlook_api.monthly_report import (
    ActionDraftSnapshot,
    VerdictSnapshot,
    build_monthly_report,
)
from portfolio_outlook_api.tax_report import ExecutionRow


def _ex(
    *,
    exec_id: str,
    side: str,
    price: str,
    qty: str,
    when: datetime,
    symbol: str = "AAPL",
    currency: str = "USD",
) -> ExecutionRow:
    return ExecutionRow(
        ibkr_exec_id=exec_id,
        account_id="DU1",
        symbol=symbol,
        side=side,
        fill_price_local=Decimal(price),
        fill_quantity=Decimal(qty),
        fill_time=when,
        commission=Decimal("1"),
        commission_currency=currency,
        action_draft_id=None,
    )


def _draft(
    *,
    draft_id: str,
    status: str = "proposed",
    created_at: datetime,
    user_approved_at: datetime | None = None,
    submission_started_at: datetime | None = None,
    terminal_state_at: datetime | None = None,
    dismissed_at: datetime | None = None,
) -> ActionDraftSnapshot:
    return ActionDraftSnapshot(
        action_draft_id=draft_id,
        status=status,
        created_at=created_at,
        user_approved_at=user_approved_at,
        submission_started_at=submission_started_at,
        terminal_state_at=terminal_state_at,
        dismissed_at=dismissed_at,
    )


def _verdict(
    *,
    decision: str = "suggest",
    when: datetime,
    confidence: float | None = 85.0,
) -> VerdictSnapshot:
    return VerdictSnapshot(
        decision=decision, generated_at=when, confidence_score_pct=confidence
    )


def test_returns_zero_metrics_when_no_data() -> None:
    report = build_monthly_report(
        year=2026,
        month=6,
        executions=(),
        action_drafts=(),
        verdicts=(),
        open_positions_count=0,
    )
    assert report.executive_summary.trade_count == 0
    assert report.executive_summary.headline_nl.startswith("Geen gesloten trades")
    assert report.income.net_local_by_currency == {}


def test_rejects_invalid_month() -> None:
    with pytest.raises(ValueError):
        build_monthly_report(
            year=2026, month=13, executions=(),
            action_drafts=(), verdicts=(), open_positions_count=0,
        )


def test_aggregates_realised_trades_only_within_month() -> None:
    executions = (
        _ex(exec_id="b1", side="BUY", price="100", qty="10",
            when=datetime(2026, 5, 10, tzinfo=UTC)),
        _ex(exec_id="s1", side="SELL", price="110", qty="10",
            when=datetime(2026, 6, 5, tzinfo=UTC)),
        _ex(exec_id="b2", side="BUY", price="100", qty="10",
            symbol="MSFT",
            when=datetime(2026, 7, 1, tzinfo=UTC)),
        _ex(exec_id="s2", side="SELL", price="120", qty="10",
            symbol="MSFT",
            when=datetime(2026, 7, 15, tzinfo=UTC)),
    )
    report = build_monthly_report(
        year=2026, month=6, executions=executions,
        action_drafts=(), verdicts=(), open_positions_count=0,
    )
    assert len(report.realised_trades) == 1
    assert report.realised_trades[0].symbol == "AAPL"
    assert report.executive_summary.trade_count == 1


def test_ytd_net_includes_earlier_months() -> None:
    executions = (
        # March trade.
        _ex(exec_id="b1", side="BUY", price="100", qty="10",
            when=datetime(2026, 2, 1, tzinfo=UTC)),
        _ex(exec_id="s1", side="SELL", price="110", qty="10",
            when=datetime(2026, 3, 10, tzinfo=UTC)),
        # June trade.
        _ex(exec_id="b2", side="BUY", price="50", qty="10", symbol="MSFT",
            when=datetime(2026, 5, 1, tzinfo=UTC)),
        _ex(exec_id="s2", side="SELL", price="55", qty="10", symbol="MSFT",
            when=datetime(2026, 6, 15, tzinfo=UTC)),
    )
    report = build_monthly_report(
        year=2026, month=6, executions=executions,
        action_drafts=(), verdicts=(), open_positions_count=0,
    )
    # Only June trade in net_local_by_currency.
    assert Decimal(report.income.net_local_by_currency["USD"]) < Decimal(
        report.income.ytd_net_local_by_currency["USD"]
    )


def test_action_draft_activity_counts_per_status_in_month() -> None:
    drafts = (
        _draft(draft_id="d1", status="proposed",
               created_at=datetime(2026, 6, 5, tzinfo=UTC)),
        _draft(draft_id="d2", status="user_approved",
               created_at=datetime(2026, 6, 6, tzinfo=UTC),
               user_approved_at=datetime(2026, 6, 7, tzinfo=UTC)),
        _draft(draft_id="d3", status="filled",
               created_at=datetime(2026, 6, 1, tzinfo=UTC),
               user_approved_at=datetime(2026, 6, 1, tzinfo=UTC),
               submission_started_at=datetime(2026, 6, 2, tzinfo=UTC),
               terminal_state_at=datetime(2026, 6, 3, tzinfo=UTC)),
        # Outside the month — shouldn't count.
        _draft(draft_id="d4", status="proposed",
               created_at=datetime(2026, 5, 15, tzinfo=UTC)),
    )
    report = build_monthly_report(
        year=2026, month=6, executions=(),
        action_drafts=drafts, verdicts=(), open_positions_count=0,
    )
    a = report.action_draft_activity
    assert a.proposed == 3
    assert a.user_approved == 2
    assert a.submitted == 1
    assert a.filled == 1


def test_verdict_activity_groups_by_decision() -> None:
    verdicts = (
        _verdict(decision="suggest",
                 when=datetime(2026, 6, 1, tzinfo=UTC)),
        _verdict(decision="suggest",
                 when=datetime(2026, 6, 2, tzinfo=UTC)),
        _verdict(decision="skip_macro_regime",
                 when=datetime(2026, 6, 3, tzinfo=UTC)),
        # Wrong month.
        _verdict(decision="suggest",
                 when=datetime(2026, 5, 28, tzinfo=UTC)),
    )
    report = build_monthly_report(
        year=2026, month=6, executions=(),
        action_drafts=(), verdicts=verdicts, open_positions_count=0,
    )
    v = report.verdict_activity
    assert v.total == 3
    assert v.by_decision["suggest"] == 2
    assert v.by_decision["skip_macro_regime"] == 1


def test_confidence_distribution_buckets_correctly() -> None:
    verdicts = (
        _verdict(when=datetime(2026, 6, 1, tzinfo=UTC), confidence=95.0),
        _verdict(when=datetime(2026, 6, 1, tzinfo=UTC), confidence=85.0),
        _verdict(when=datetime(2026, 6, 1, tzinfo=UTC), confidence=75.0),
        _verdict(when=datetime(2026, 6, 1, tzinfo=UTC), confidence=50.0),
    )
    report = build_monthly_report(
        year=2026, month=6, executions=(),
        action_drafts=(), verdicts=verdicts, open_positions_count=0,
    )
    dist = report.software_performance.confidence_distribution_pct
    assert dist[">=90%"] == 25.0
    assert dist["80-90%"] == 25.0
    assert dist["70-80%"] == 25.0
    assert dist["<60%"] == 25.0


def test_hit_rate_computed_only_on_in_month_trades() -> None:
    executions = (
        # +10% net on cost > 4% target.
        _ex(exec_id="b1", side="BUY", price="100", qty="10",
            when=datetime(2026, 5, 10, tzinfo=UTC)),
        _ex(exec_id="s1", side="SELL", price="111", qty="10",
            when=datetime(2026, 6, 5, tzinfo=UTC)),
        # +1% net below target.
        _ex(exec_id="b2", side="BUY", price="100", qty="10", symbol="MSFT",
            when=datetime(2026, 5, 10, tzinfo=UTC)),
        _ex(exec_id="s2", side="SELL", price="101", qty="10", symbol="MSFT",
            when=datetime(2026, 6, 15, tzinfo=UTC)),
    )
    report = build_monthly_report(
        year=2026, month=6, executions=executions,
        action_drafts=(), verdicts=(), open_positions_count=0,
    )
    assert report.executive_summary.hit_rate_pct == 50.0


def test_baseline_comparison_text_when_eur_present() -> None:
    executions = (
        _ex(exec_id="b1", side="BUY", price="100", qty="10",
            when=datetime(2026, 5, 1, tzinfo=UTC), currency="EUR"),
        _ex(exec_id="s1", side="SELL", price="125", qty="10",
            when=datetime(2026, 6, 15, tzinfo=UTC), currency="EUR"),
    )
    report = build_monthly_report(
        year=2026, month=6, executions=executions,
        action_drafts=(), verdicts=(), open_positions_count=0,
        baseline_monthly_eur=Decimal("100"),
    )
    text = report.executive_summary.vs_baseline_eur
    assert text is not None
    assert "baseline" in text.lower()


def test_baseline_comparison_text_none_when_only_usd_trades() -> None:
    executions = (
        _ex(exec_id="b1", side="BUY", price="100", qty="10",
            when=datetime(2026, 5, 1, tzinfo=UTC), currency="USD"),
        _ex(exec_id="s1", side="SELL", price="120", qty="10",
            when=datetime(2026, 6, 15, tzinfo=UTC), currency="USD"),
    )
    report = build_monthly_report(
        year=2026, month=6, executions=executions,
        action_drafts=(), verdicts=(), open_positions_count=0,
    )
    assert report.executive_summary.vs_baseline_eur is None


def test_open_positions_count_passed_through() -> None:
    report = build_monthly_report(
        year=2026, month=6, executions=(),
        action_drafts=(), verdicts=(), open_positions_count=7,
    )
    assert report.open_positions_count == 7


def test_notes_warn_about_fx_and_dividends() -> None:
    report = build_monthly_report(
        year=2026, month=6, executions=(),
        action_drafts=(), verdicts=(), open_positions_count=0,
    )
    assert any("EUR" in note for note in report.notes_nl)
    assert any("Dividenden" in note for note in report.notes_nl)
