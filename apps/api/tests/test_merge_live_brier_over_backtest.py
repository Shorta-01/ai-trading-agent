"""Tests for the live-Brier-over-backtest merge (V1.2 §D)."""

from __future__ import annotations

from decimal import Decimal

from portfolio_outlook_api.ensemble_forecast import (
    merge_live_brier_over_backtest,
)


def test_empty_both_returns_empty() -> None:
    assert merge_live_brier_over_backtest(
        live_history={}, backtest_history={}
    ) == {}


def test_only_backtest_returns_backtest() -> None:
    backtest = {"gbm": Decimal("0.22"), "momentum": Decimal("0.27")}
    out = merge_live_brier_over_backtest(
        live_history={}, backtest_history=backtest
    )
    assert out == backtest
    # Must not mutate the input.
    assert backtest == {"gbm": Decimal("0.22"), "momentum": Decimal("0.27")}


def test_only_live_returns_live() -> None:
    live = {"gbm": Decimal("0.18"), "qvm": Decimal("0.31")}
    out = merge_live_brier_over_backtest(
        live_history=live, backtest_history={}
    )
    assert out == live


def test_live_takes_precedence_per_model() -> None:
    """The whole point: when both maps have a predictor, live wins.
    Other predictors continue to use the backtest cold-start."""

    backtest = {
        "gbm": Decimal("0.30"),  # will be overridden by live
        "momentum": Decimal("0.25"),  # only in backtest, kept
    }
    live = {
        "gbm": Decimal("0.18"),  # overrides backtest
        "qvm": Decimal("0.22"),  # only in live, kept
    }
    out = merge_live_brier_over_backtest(
        live_history=live, backtest_history=backtest
    )
    assert out == {
        "gbm": Decimal("0.18"),  # live wins
        "momentum": Decimal("0.25"),  # backtest fallback
        "qvm": Decimal("0.22"),  # live-only
    }


def test_input_dicts_not_mutated() -> None:
    """The function must not mutate either input; callers may use them
    elsewhere (logging, audit). Defensive copy contract."""

    backtest = {"gbm": Decimal("0.30")}
    live = {"gbm": Decimal("0.18")}
    backtest_snapshot = dict(backtest)
    live_snapshot = dict(live)
    merge_live_brier_over_backtest(
        live_history=live, backtest_history=backtest
    )
    assert backtest == backtest_snapshot
    assert live == live_snapshot
