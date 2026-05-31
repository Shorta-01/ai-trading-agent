"""Unit tests for the morning-chain alerts compute function."""

from __future__ import annotations

from dataclasses import dataclass

from portfolio_outlook_worker.morning_alerts import compute_morning_alerts


@dataclass
class _Suggestion:
    ibkr_conid: str
    symbol: str
    action_label_nl: str
    confidence_label: str = "high"
    status: str = "ready"


def test_returns_empty_when_nothing_actionable() -> None:
    suggestions = [
        _Suggestion("aapl", "AAPL", "Houden", confidence_label="high"),
        _Suggestion("msft", "MSFT", "Bekijken", confidence_label="medium"),
    ]
    alerts = compute_morning_alerts(
        suggestions=suggestions, held_conids={"aapl", "msft"}
    )
    assert alerts == []


def test_high_conf_sell_on_held_fires_alert() -> None:
    suggestions = [
        _Suggestion("aapl", "AAPL", "Verkopen", confidence_label="high"),
        _Suggestion("msft", "MSFT", "Verminderen", confidence_label="high"),
    ]
    alerts = compute_morning_alerts(
        suggestions=suggestions, held_conids={"aapl", "msft"}
    )
    kinds = {a["kind"] for a in alerts}
    assert "high_confidence_sell_morning" in kinds
    sell_alert = next(
        a for a in alerts if a["kind"] == "high_confidence_sell_morning"
    )
    assert "2 verkoop-suggestie" in sell_alert["title_nl"]
    # The symbol list is sorted + de-duplicated.
    assert "AAPL" in sell_alert["body_nl"]
    assert "MSFT" in sell_alert["body_nl"]


def test_high_conf_sell_on_non_held_does_NOT_fire() -> None:
    """A Verkopen suggestion on an asset I don't own isn't actionable
    — there's nothing to sell. Only held positions trigger the alert."""

    suggestions = [
        _Suggestion("xyz", "XYZ", "Verkopen", confidence_label="high"),
    ]
    alerts = compute_morning_alerts(
        suggestions=suggestions, held_conids={"aapl"}
    )
    assert alerts == []


def test_medium_conf_sell_does_NOT_fire() -> None:
    """Only HIGH-confidence sells trigger the morning email; medium
    confidence stays in the suggestions grid."""

    suggestions = [
        _Suggestion("aapl", "AAPL", "Verkopen", confidence_label="medium"),
    ]
    alerts = compute_morning_alerts(
        suggestions=suggestions, held_conids={"aapl"}
    )
    assert alerts == []


def test_high_conf_buy_on_non_held_fires_alert() -> None:
    suggestions = [
        _Suggestion("nvda", "NVDA", "Kopen", confidence_label="high"),
    ]
    alerts = compute_morning_alerts(
        suggestions=suggestions, held_conids={"aapl"}
    )
    kinds = {a["kind"] for a in alerts}
    assert "new_high_confidence_buy" in kinds


def test_high_conf_buy_on_held_does_NOT_fire_buy_alert() -> None:
    """Kopen on a position I already own routes to ``Langzaam bijkopen``
    upstream, not Kopen — so this should never happen, but if it
    does we don't double-fire."""

    suggestions = [
        _Suggestion("aapl", "AAPL", "Kopen", confidence_label="high"),
    ]
    alerts = compute_morning_alerts(
        suggestions=suggestions, held_conids={"aapl"}
    )
    kinds = {a["kind"] for a in alerts}
    assert "new_high_confidence_buy" not in kinds


def test_chain_failure_alert_is_independent_of_suggestions() -> None:
    """Even with zero suggestions and zero positions, a chain failure
    still produces an alert so the operator notices the silent
    failure."""

    alerts = compute_morning_alerts(
        suggestions=[],
        held_conids=set(),
        chain_failed=True,
        failure_reason_nl="Voorspellings-stap heeft een fout.",
    )
    kinds = {a["kind"] for a in alerts}
    assert "morning_chain_failure" in kinds
    failure_alert = next(
        a for a in alerts if a["kind"] == "morning_chain_failure"
    )
    assert "Voorspellings-stap" in failure_alert["body_nl"]


def test_blocked_suggestions_are_ignored() -> None:
    """A blocked suggestion never produces an alert even at high
    confidence — the operator can't act on Geblokkeerd."""

    suggestions = [
        _Suggestion(
            "aapl",
            "AAPL",
            "Verkopen",
            confidence_label="high",
            status="blocked",
        ),
    ]
    alerts = compute_morning_alerts(
        suggestions=suggestions, held_conids={"aapl"}
    )
    assert alerts == []


def test_multiple_alert_kinds_can_fire_together() -> None:
    suggestions = [
        _Suggestion("aapl", "AAPL", "Verkopen", confidence_label="high"),
        _Suggestion("nvda", "NVDA", "Kopen", confidence_label="high"),
    ]
    alerts = compute_morning_alerts(
        suggestions=suggestions,
        held_conids={"aapl"},
        chain_failed=True,
        failure_reason_nl="Test failure.",
    )
    kinds = {a["kind"] for a in alerts}
    assert kinds == {
        "morning_chain_failure",
        "high_confidence_sell_morning",
        "new_high_confidence_buy",
    }
