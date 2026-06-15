"""Pure-Python unit tests for the tax-year report engine (V1.2 §AW)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_outlook_api.tax_report import (
    ExecutionRow,
    build_tax_year_report,
)


def _ex(
    *,
    exec_id: str,
    symbol: str,
    side: str,
    price: str,
    qty: str,
    when: datetime,
    currency: str = "USD",
    account: str = "DU1",
    action_draft_id: str | None = None,
) -> ExecutionRow:
    return ExecutionRow(
        ibkr_exec_id=exec_id,
        account_id=account,
        symbol=symbol,
        side=side,
        fill_price_local=Decimal(price),
        fill_quantity=Decimal(qty),
        fill_time=when,
        commission=Decimal("1"),
        commission_currency=currency,
        action_draft_id=action_draft_id,
    )


def test_returns_empty_report_when_no_executions() -> None:
    report = build_tax_year_report(year=2026, executions=())
    assert report.realised_trades == ()
    assert report.year_totals.trade_count == 0
    assert len(report.monthly_points) == 12
    assert report.good_householder.trades_per_year == 0
    assert any("dividenden" in note.lower() for note in report.notes_nl)


def test_matches_one_buy_to_one_sell_with_correct_tob() -> None:
    buy_time = datetime(2026, 1, 10, 15, 0, tzinfo=UTC)
    sell_time = datetime(2026, 3, 15, 15, 0, tzinfo=UTC)
    executions = (
        _ex(exec_id="b1", symbol="AAPL", side="BUY", price="100", qty="10", when=buy_time),
        _ex(exec_id="s1", symbol="AAPL", side="SELL", price="108", qty="10", when=sell_time),
    )
    report = build_tax_year_report(year=2026, executions=executions)
    assert len(report.realised_trades) == 1
    trade = report.realised_trades[0]
    # gross = 10 * (108-100) = 80.
    assert trade.gross_local == Decimal("80.00")
    # TOB = 0.35% on each leg. Buy notional = 1000, TOB = 3.50.
    # Sell notional = 1080, TOB = 3.78.
    assert trade.tob_buy_local == Decimal("3.50")
    assert trade.tob_sell_local == Decimal("3.78")
    # Net = 80 - 3.50 - 3.78 = 72.72.
    assert trade.net_local == Decimal("72.72")
    assert trade.hold_days == 64
    # 72.72 / 1000 * 100 = 7.27%.
    assert trade.net_pct_on_cost == Decimal("7.27")


def test_fifo_matches_oldest_buy_first() -> None:
    """Two BUYs at different prices, then one SELL — the oldest lot
    matches first."""

    executions = (
        _ex(
            exec_id="b1", symbol="AAPL", side="BUY", price="100", qty="5",
            when=datetime(2026, 1, 10, tzinfo=UTC),
        ),
        _ex(
            exec_id="b2", symbol="AAPL", side="BUY", price="120", qty="5",
            when=datetime(2026, 2, 10, tzinfo=UTC),
        ),
        _ex(
            exec_id="s1", symbol="AAPL", side="SELL", price="125", qty="5",
            when=datetime(2026, 3, 10, tzinfo=UTC),
        ),
    )
    trades = build_tax_year_report(year=2026, executions=executions).realised_trades
    assert len(trades) == 1
    # 5 shares matched against b1 (oldest, price=100).
    assert trades[0].buy_exec_id == "b1"
    assert trades[0].buy_price_local == Decimal("100")
    assert trades[0].gross_local == Decimal("125.00")


def test_partial_sell_splits_buy_lot() -> None:
    """One BUY of 10, then SELL of 6 — leaves 4 shares open."""

    executions = (
        _ex(
            exec_id="b1", symbol="AAPL", side="BUY", price="100", qty="10",
            when=datetime(2026, 1, 10, tzinfo=UTC),
        ),
        _ex(
            exec_id="s1", symbol="AAPL", side="SELL", price="110", qty="6",
            when=datetime(2026, 3, 10, tzinfo=UTC),
        ),
    )
    trades = build_tax_year_report(year=2026, executions=executions).realised_trades
    assert len(trades) == 1
    assert trades[0].quantity == Decimal("6")
    # gross = 6 * 10 = 60.
    assert trades[0].gross_local == Decimal("60.00")


def test_sell_spans_two_buy_lots() -> None:
    """SELL larger than the oldest BUY — emits one row per buy lot
    matched."""

    executions = (
        _ex(
            exec_id="b1", symbol="AAPL", side="BUY", price="100", qty="3",
            when=datetime(2026, 1, 10, tzinfo=UTC),
        ),
        _ex(
            exec_id="b2", symbol="AAPL", side="BUY", price="110", qty="5",
            when=datetime(2026, 2, 10, tzinfo=UTC),
        ),
        _ex(
            exec_id="s1", symbol="AAPL", side="SELL", price="120", qty="6",
            when=datetime(2026, 3, 10, tzinfo=UTC),
        ),
    )
    trades = build_tax_year_report(year=2026, executions=executions).realised_trades
    assert len(trades) == 2
    # First row matches b1: 3 shares × (120-100) = 60.
    assert trades[0].buy_exec_id == "b1"
    assert trades[0].quantity == Decimal("3")
    # Second row matches b2: 3 shares × (120-110) = 30.
    assert trades[1].buy_exec_id == "b2"
    assert trades[1].quantity == Decimal("3")


def test_only_closed_trades_in_year_are_returned() -> None:
    """BUY in 2025, SELL in 2026 — the report for 2026 picks it up
    even though the BUY was earlier. Year 2025 report has no rows."""

    executions = (
        _ex(
            exec_id="b1", symbol="AAPL", side="BUY", price="100", qty="10",
            when=datetime(2025, 12, 15, tzinfo=UTC),
        ),
        _ex(
            exec_id="s1", symbol="AAPL", side="SELL", price="110", qty="10",
            when=datetime(2026, 1, 20, tzinfo=UTC),
        ),
    )
    assert (
        len(build_tax_year_report(year=2025, executions=executions).realised_trades)
        == 0
    )
    report_2026 = build_tax_year_report(year=2026, executions=executions)
    assert len(report_2026.realised_trades) == 1
    assert report_2026.realised_trades[0].sell_date.year == 2026


def test_aggregates_per_currency() -> None:
    executions = (
        _ex(
            exec_id="b1", symbol="AAPL", side="BUY", price="100", qty="10",
            when=datetime(2026, 1, 10, tzinfo=UTC), currency="USD",
        ),
        _ex(
            exec_id="s1", symbol="AAPL", side="SELL", price="110", qty="10",
            when=datetime(2026, 3, 10, tzinfo=UTC), currency="USD",
        ),
        _ex(
            exec_id="b2", symbol="ASML", side="BUY", price="600", qty="2",
            when=datetime(2026, 1, 10, tzinfo=UTC), currency="EUR",
        ),
        _ex(
            exec_id="s2", symbol="ASML", side="SELL", price="700", qty="2",
            when=datetime(2026, 5, 10, tzinfo=UTC), currency="EUR",
        ),
    )
    totals = build_tax_year_report(year=2026, executions=executions).year_totals
    assert "USD" in totals.gross_local_by_currency
    assert "EUR" in totals.gross_local_by_currency
    assert totals.trade_count == 2


def test_monthly_breakdown_has_12_points_with_cumulative() -> None:
    executions = (
        _ex(
            exec_id="b1", symbol="AAPL", side="BUY", price="100", qty="10",
            when=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        _ex(
            exec_id="s1", symbol="AAPL", side="SELL", price="110", qty="10",
            when=datetime(2026, 3, 15, tzinfo=UTC),
        ),
    )
    points = build_tax_year_report(year=2026, executions=executions).monthly_points
    assert len(points) == 12
    # Trade closed in March → cumulative becomes non-zero from March on.
    feb = points[1]
    march = points[2]
    apr = points[3]
    assert feb.cumulative_net_local_by_currency.get("USD", "0.00") == "0.00"
    assert march.cumulative_net_local_by_currency["USD"] != "0.00"
    assert (
        march.cumulative_net_local_by_currency["USD"]
        == apr.cumulative_net_local_by_currency["USD"]
    )


def test_hit_rate_counts_trades_at_or_above_4_pct() -> None:
    executions = (
        # 7.27% net → hit.
        _ex(
            exec_id="b1", symbol="A", side="BUY", price="100", qty="10",
            when=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        _ex(
            exec_id="s1", symbol="A", side="SELL", price="108", qty="10",
            when=datetime(2026, 2, 1, tzinfo=UTC),
        ),
        # ~1.3% net → miss.
        _ex(
            exec_id="b2", symbol="B", side="BUY", price="100", qty="10",
            when=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        _ex(
            exec_id="s2", symbol="B", side="SELL", price="102", qty="10",
            when=datetime(2026, 2, 1, tzinfo=UTC),
        ),
    )
    totals = build_tax_year_report(year=2026, executions=executions).year_totals
    assert totals.trade_count == 2
    assert totals.hit_rate_pct == 50.0


def test_good_householder_metrics_summarise_doctrine() -> None:
    executions = (
        _ex(
            exec_id="b1", symbol="A", side="BUY", price="100", qty="10",
            when=datetime(2026, 1, 10, tzinfo=UTC),
        ),
        _ex(
            exec_id="s1", symbol="A", side="SELL", price="110", qty="10",
            when=datetime(2026, 3, 20, tzinfo=UTC),
        ),
    )
    report = build_tax_year_report(
        year=2026,
        executions=executions,
        trading_capital_eur=Decimal("50000"),
        total_wealth_eur=Decimal("6000000"),
    )
    hh = report.good_householder
    assert hh.uses_leverage is False
    assert hh.uses_shorts is False
    assert hh.trading_capital_share_pct == pytest.approx(0.8, abs=0.1)
    assert "trade" in hh.summary_nl


def test_notes_warn_when_fx_conversion_unavailable() -> None:
    report = build_tax_year_report(
        year=2026, executions=(), fx_conversion_available=False
    )
    assert any("EUR-conversie" in note for note in report.notes_nl)


def test_excess_sell_without_matching_buy_is_skipped() -> None:
    """Operator paper-doctrine forbids shorts, so a SELL that
    outstrips the available BUY lots should be quietly ignored."""

    executions = (
        _ex(
            exec_id="b1", symbol="A", side="BUY", price="100", qty="2",
            when=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        _ex(
            exec_id="s1", symbol="A", side="SELL", price="110", qty="5",
            when=datetime(2026, 2, 1, tzinfo=UTC),
        ),
    )
    trades = build_tax_year_report(year=2026, executions=executions).realised_trades
    # Only the 2 shares that have a matching BUY are reported.
    assert len(trades) == 1
    assert trades[0].quantity == Decimal("2")


def test_ibkr_config_audit_passes_through_to_report() -> None:
    """V1.2 §BZ vervolg — ``ibkr_config_audit`` entries die meegegeven
    worden moeten in de TaxYearReport landen zodat PDF + CSV ze kunnen
    renderen voor de accountant."""

    from portfolio_outlook_api.tax_report import IbkrConfigAuditEntry

    entries = (
        IbkrConfigAuditEntry(
            created_at="2026-03-12T10:00:00+00:00",
            event_code="account_id_mismatch",
            severity="warning",
            status="resolved",
            source="api:ibkr_sync",
            title_nl="Mismatch",
            message_nl="DU1234567 vs U7654321",
        ),
        IbkrConfigAuditEntry(
            created_at="2026-05-01T09:00:00+00:00",
            event_code="ibkr_account_id_changed",
            severity="info",
            status="open",
            source="api:runtime_config_routes",
            title_nl="Account-id gewijzigd",
            message_nl="DU1111111 -> DU2222222",
        ),
    )
    report = build_tax_year_report(
        year=2026,
        executions=(),
        ibkr_config_audit=entries,
    )
    assert report.ibkr_config_audit == entries


def test_ibkr_config_audit_defaults_to_empty_when_not_supplied() -> None:
    """Backwards-compat: een report zonder audit-trail moet nog steeds
    correct opgebouwd worden (default tuple-leeg)."""

    report = build_tax_year_report(year=2026, executions=())
    assert report.ibkr_config_audit == ()
