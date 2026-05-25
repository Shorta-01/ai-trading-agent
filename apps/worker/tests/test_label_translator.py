"""Task 130 — deterministic label-translator table-driven tests."""

from __future__ import annotations

from decimal import Decimal

from portfolio_outlook_worker.forecasting.historical_bootstrap import (
    BootstrapForecastResult,
)
from portfolio_outlook_worker.forecasting.label_translator import (
    derive_confidence,
    translate_to_label,
)


def _f(
    *,
    p10: str = "-0.05",
    p50: str = "0.02",
    p90: str = "0.07",
    prob_positive: str = "0.60",
    prob_loss: str = "0.10",
    vol: str = "0.20",
    history: int = 252,
) -> BootstrapForecastResult:
    return BootstrapForecastResult(
        history_closes_count=history,
        horizon_days=20,
        p10_log_return=Decimal(p10),
        p50_log_return=Decimal(p50),
        p90_log_return=Decimal(p90),
        prob_positive=Decimal(prob_positive),
        prob_loss_gt_5pct=Decimal(prob_loss),
        expected_volatility_annualized=Decimal(vol),
    )


def _translate(  # type: ignore[no-untyped-def]
    *,
    forecast: BootstrapForecastResult,
    user_holds: bool = False,
    freshness: str = "fresh",
    confidence: str = "Hoog",
):
    return translate_to_label(
        forecast=forecast,
        user_holds_position=user_holds,
        freshness=freshness,  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
        history_closes_count=forecast.history_closes_count,
    )


# ---- block_reason takes precedence -------------------------------


def test_stale_freshness_blocks_with_data_stale_reason() -> None:
    result = _translate(forecast=_f(prob_positive="0.66"), freshness="stale")
    assert result.label == "Geblokkeerd"
    assert result.block_reason == "data_stale"


def test_unavailable_freshness_blocks_with_data_unavailable_reason() -> None:
    result = _translate(
        forecast=_f(prob_positive="0.66"), freshness="unavailable"
    )
    assert result.label == "Geblokkeerd"
    assert result.block_reason == "data_unavailable"


def test_insufficient_history_blocks_even_when_signal_is_strong() -> None:
    forecast = _f(prob_positive="0.90", history=150)
    result = _translate(forecast=forecast)
    assert result.label == "Geblokkeerd"
    assert result.block_reason == "insufficient_history"


def test_implausible_volatility_blocks() -> None:
    result = _translate(forecast=_f(prob_positive="0.66", vol="0.85"))
    assert result.label == "Geblokkeerd"
    assert result.block_reason == "implausible_volatility"


# ---- Kopen ------------------------------------------------------


def test_kopen_when_strong_positive_signal_and_no_holding() -> None:
    result = _translate(
        forecast=_f(prob_positive="0.66", p50="0.03", prob_loss="0.10"),
        user_holds=False,
    )
    assert result.label == "Kopen"
    assert result.block_reason is None


def test_kopen_when_strong_positive_signal_and_already_holding() -> None:
    """Kopen rule fires regardless of holding status (per §Q4 spec)."""

    result = _translate(
        forecast=_f(prob_positive="0.70", p50="0.04", prob_loss="0.10"),
        user_holds=True,
    )
    assert result.label == "Kopen"


def test_kopen_does_NOT_fire_when_prob_loss_too_high() -> None:
    result = _translate(
        forecast=_f(prob_positive="0.70", p50="0.04", prob_loss="0.20")
    )
    assert result.label != "Kopen"


def test_kopen_does_NOT_fire_when_p50_negative() -> None:
    result = _translate(
        forecast=_f(prob_positive="0.70", p50="-0.01", prob_loss="0.10")
    )
    assert result.label != "Kopen"


def test_kopen_does_NOT_fire_when_prob_positive_below_threshold() -> None:
    result = _translate(
        forecast=_f(prob_positive="0.64", p50="0.04", prob_loss="0.10")
    )
    assert result.label != "Kopen"


# ---- Verminderen ------------------------------------------------


def test_verminderen_when_weak_negative_signal_and_holding() -> None:
    result = _translate(
        forecast=_f(prob_positive="0.30", p50="-0.02", prob_loss="0.20"),
        user_holds=True,
    )
    assert result.label == "Verminderen"


def test_verminderen_does_NOT_fire_when_user_does_not_hold() -> None:
    result = _translate(
        forecast=_f(prob_positive="0.30", p50="-0.02"),
        user_holds=False,
    )
    assert result.label == "Bekijken"


# ---- Verkopen ---------------------------------------------------


def test_verkopen_when_strong_negative_signal_high_loss_and_holding() -> None:
    result = _translate(
        forecast=_f(
            prob_positive="0.20", p50="-0.05", prob_loss="0.50"
        ),
        user_holds=True,
    )
    assert result.label == "Verkopen"


def test_verkopen_does_NOT_fire_without_holding() -> None:
    result = _translate(
        forecast=_f(
            prob_positive="0.20", p50="-0.05", prob_loss="0.50"
        ),
        user_holds=False,
    )
    assert result.label == "Bekijken"


def test_verkopen_does_NOT_fire_when_prob_loss_below_threshold() -> None:
    result = _translate(
        forecast=_f(
            prob_positive="0.20", p50="-0.05", prob_loss="0.30"
        ),
        user_holds=True,
    )
    # Falls through to Verminderen (which also requires holding).
    assert result.label == "Verminderen"


# ---- Houden + Bekijken -------------------------------------------


def test_houden_when_holding_and_no_sell_trigger() -> None:
    result = _translate(
        forecast=_f(prob_positive="0.50", p50="0.01"), user_holds=True
    )
    assert result.label == "Houden"


def test_bekijken_when_not_holding_and_no_kopen_trigger() -> None:
    result = _translate(
        forecast=_f(prob_positive="0.50", p50="0.01"), user_holds=False
    )
    assert result.label == "Bekijken"


# ---- confidence -------------------------------------------------


def test_derive_confidence_hoog_when_full_history_no_gaps() -> None:
    assert (
        derive_confidence(
            history_closes_count=252,
            gaps_in_last_60_days=0,
            expected_volatility_annualized=Decimal("0.20"),
        )
        == "Hoog"
    )


def test_derive_confidence_gemiddeld_when_partial_history() -> None:
    assert (
        derive_confidence(
            history_closes_count=210,
            gaps_in_last_60_days=1,
            expected_volatility_annualized=Decimal("0.20"),
        )
        == "Gemiddeld"
    )


def test_derive_confidence_laag_when_too_few_closes() -> None:
    assert (
        derive_confidence(
            history_closes_count=150,
            gaps_in_last_60_days=0,
            expected_volatility_annualized=Decimal("0.20"),
        )
        == "Laag"
    )


def test_derive_confidence_demotes_high_vol_to_gemiddeld() -> None:
    assert (
        derive_confidence(
            history_closes_count=252,
            gaps_in_last_60_days=0,
            expected_volatility_annualized=Decimal("0.45"),
        )
        == "Gemiddeld"
    )
