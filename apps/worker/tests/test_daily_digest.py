"""Tests for the pure daily-digest compute function."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from portfolio_outlook_worker.daily_digest import compute_daily_digest_payload


@dataclass
class _FakePosition:
    symbol: str
    currency: str
    pnl_pct: Decimal | None = None
    pnl_abs: Decimal | None = None


@dataclass
class _FakeSuggestion:
    action_label_nl: str
    confidence_label: str = "medium"


@dataclass
class _FakeDraft:
    state: str


_NOW = datetime(2026, 5, 31, 17, 45, tzinfo=UTC)


def _base_payload_kwargs(**overrides) -> dict:
    defaults = dict(
        ibkr_account_ref="DU1234567",
        market_code="EURONEXT",
        briefing_date=date(2026, 5, 31),
        generated_at=_NOW,
        today_nav=Decimal("100000.00"),
        prev_nav=Decimal("100500.00"),
        base_currency="EUR",
        positions=[],
        suggestions=[],
        action_drafts=[],
    )
    defaults.update(overrides)
    return defaults


def test_returns_payload_with_required_keys() -> None:
    payload = compute_daily_digest_payload(**_base_payload_kwargs())
    expected_keys = {
        "digest_id",
        "ibkr_account_ref",
        "market_code",
        "briefing_date",
        "generated_at",
        "nav_summary_json",
        "positions_summary_json",
        "suggestions_summary_json",
        "action_drafts_summary_json",
        "alerts_json",
        "status",
        "blocking_reason",
    }
    assert set(payload.keys()) == expected_keys


def test_nav_summary_computes_delta_in_percent() -> None:
    payload = compute_daily_digest_payload(
        **_base_payload_kwargs(
            today_nav=Decimal("100000.00"),
            prev_nav=Decimal("100500.00"),
        )
    )
    nav = payload["nav_summary_json"]
    assert nav["currency"] == "EUR"
    assert nav["total_nav"] == "100000.00"
    assert nav["delta_abs"] == "-500.00"
    # -500 / 100500 * 100 ≈ -0.4975%, rounded to -0.50%.
    assert nav["delta_pct"] == "-0.50"


def test_status_is_partial_when_nav_is_missing() -> None:
    payload = compute_daily_digest_payload(
        **_base_payload_kwargs(today_nav=None, prev_nav=Decimal("100000.00"))
    )
    assert payload["status"] == "partial"
    assert payload["blocking_reason"] == "missing_nav_snapshot"
    assert payload["nav_summary_json"]["delta_pct"] is None


def test_top_winners_and_losers_are_sorted_correctly() -> None:
    positions = [
        _FakePosition("AAPL", "USD", Decimal("3.50"), Decimal("120.00")),
        _FakePosition("MSFT", "USD", Decimal("-2.10"), Decimal("-80.00")),
        _FakePosition("GOOG", "USD", Decimal("8.00"), Decimal("300.00")),
        _FakePosition("AMZN", "USD", Decimal("-6.00"), Decimal("-220.00")),
        _FakePosition("META", "USD", None, None),  # dropped (no PnL)
    ]
    payload = compute_daily_digest_payload(
        **_base_payload_kwargs(positions=positions)
    )
    positions_summary = payload["positions_summary_json"]
    assert positions_summary["position_count"] == 5
    # Top winners sorted descending.
    winners = positions_summary["top_winners"]
    assert winners[0]["symbol"] == "GOOG"
    assert winners[1]["symbol"] == "AAPL"
    # Top losers sorted ascending (worst first).
    losers = positions_summary["top_losers"]
    assert losers[0]["symbol"] == "AMZN"
    assert losers[1]["symbol"] == "MSFT"


def test_suggestions_summary_counts_by_action_label() -> None:
    suggestions = [
        _FakeSuggestion("Kopen", "high"),
        _FakeSuggestion("Verkopen", "high"),
        _FakeSuggestion("Houden", "medium"),
        _FakeSuggestion("Bekijken", "low"),
    ]
    payload = compute_daily_digest_payload(
        **_base_payload_kwargs(suggestions=suggestions)
    )
    summary = payload["suggestions_summary_json"]
    assert summary["total"] == 4
    assert summary["by_action_label"]["Kopen"] == 1
    assert summary["by_action_label"]["Verkopen"] == 1
    assert summary["high_confidence_count"] == 2


def test_action_drafts_summary_buckets_by_state() -> None:
    drafts = [
        _FakeDraft("draft"),
        _FakeDraft("approved"),
        _FakeDraft("submitted_to_broker"),
        _FakeDraft("cancelled"),
        _FakeDraft("draft"),
    ]
    payload = compute_daily_digest_payload(
        **_base_payload_kwargs(action_drafts=drafts)
    )
    summary = payload["action_drafts_summary_json"]
    assert summary["created_today"] == 2
    assert summary["approved_today"] == 1
    assert summary["submitted_today"] == 1
    assert summary["cancelled_today"] == 1


def test_nav_drop_alert_fires_when_delta_below_threshold() -> None:
    payload = compute_daily_digest_payload(
        **_base_payload_kwargs(
            today_nav=Decimal("98000.00"),  # 2% drop
            prev_nav=Decimal("100000.00"),
        )
    )
    alert_kinds = {a["kind"] for a in payload["alerts_json"]}
    assert "nav_drop" in alert_kinds


def test_high_confidence_sell_alert_fires_on_verkopen() -> None:
    suggestions = [
        _FakeSuggestion("Verkopen", "high"),
        _FakeSuggestion("Houden", "high"),
    ]
    payload = compute_daily_digest_payload(
        **_base_payload_kwargs(suggestions=suggestions)
    )
    alert_kinds = {a["kind"] for a in payload["alerts_json"]}
    assert "high_confidence_sell" in alert_kinds


def test_position_drop_alert_fires_on_first_loser_below_threshold() -> None:
    positions = [
        _FakePosition("AAPL", "USD", Decimal("-6.50"), Decimal("-200.00")),
    ]
    payload = compute_daily_digest_payload(
        **_base_payload_kwargs(positions=positions)
    )
    alert_kinds = {a["kind"] for a in payload["alerts_json"]}
    assert "position_drop" in alert_kinds
    drop = next(
        a for a in payload["alerts_json"] if a["kind"] == "position_drop"
    )
    assert drop["reference_id"] == "AAPL"


def test_no_alerts_fire_on_quiet_day() -> None:
    payload = compute_daily_digest_payload(
        **_base_payload_kwargs(
            today_nav=Decimal("100050.00"),  # +0.05%
            prev_nav=Decimal("100000.00"),
        )
    )
    assert payload["alerts_json"] == []
    assert payload["status"] == "ready"


def test_digest_id_is_uuid_prefixed() -> None:
    payload = compute_daily_digest_payload(**_base_payload_kwargs())
    assert payload["digest_id"].startswith("digest_")
    assert len(payload["digest_id"]) > len("digest_")
