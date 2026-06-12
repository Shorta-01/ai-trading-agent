"""Tests for the news-sentiment booster (V1.2 §S)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    NewsItem,
    apply_buy_bias_to_confidence,
    compute_news_buy_bias,
)

# ---- compute_news_buy_bias -------------------------------------------


def test_empty_batch_returns_zero_bias() -> None:
    score = compute_news_buy_bias([])
    assert score.total_items == 0
    assert score.bullish_count == 0
    assert score.buy_bias == Decimal("0.00")
    assert score.matched_keywords == ()


def test_no_bullish_keywords_returns_zero_bias() -> None:
    score = compute_news_buy_bias(
        [
            NewsItem(title="Quarterly report filed"),
            NewsItem(title="New product launch"),
        ]
    )
    assert score.bullish_count == 0
    assert score.buy_bias == Decimal("0.00")


def test_analyst_upgrade_classified_as_bullish() -> None:
    score = compute_news_buy_bias(
        [NewsItem(title="Morgan Stanley analyst upgrade")]
    )
    assert score.bullish_count == 1
    assert score.buy_bias == Decimal("1.00")
    assert "analyst upgrade" in score.matched_keywords


def test_dividend_hike_classified_as_bullish() -> None:
    score = compute_news_buy_bias(
        [NewsItem(title="Board approves dividend hike")]
    )
    assert score.bullish_count == 1


def test_insider_buying_classified_as_bullish() -> None:
    score = compute_news_buy_bias([NewsItem(title="CEO buys 50,000 shares")])
    assert score.bullish_count == 1


def test_buyback_classified_as_bullish() -> None:
    score = compute_news_buy_bias(
        [NewsItem(title="Company announces share buyback")]
    )
    assert score.bullish_count == 1


def test_fda_approval_classified_as_bullish() -> None:
    score = compute_news_buy_bias(
        [NewsItem(title="FDA approval for new drug")]
    )
    assert score.bullish_count == 1


def test_contract_win_classified_as_bullish() -> None:
    score = compute_news_buy_bias([NewsItem(title="Major contract win")])
    assert score.bullish_count == 1


def test_dutch_dividend_verhoogd_classified_as_bullish() -> None:
    score = compute_news_buy_bias(
        [NewsItem(title="Bedrijf heeft dividend verhoogd")]
    )
    assert score.bullish_count == 1


def test_partial_bullish_batch_gives_proportional_bias() -> None:
    # 1 bullish out of 4 → bias = 0.25.
    score = compute_news_buy_bias(
        [
            NewsItem(title="Quarterly report filed"),
            NewsItem(title="New CEO appointed"),
            NewsItem(title="Analyst upgrade for stock"),
            NewsItem(title="Industry overview piece"),
        ]
    )
    assert score.bullish_count == 1
    assert score.buy_bias == Decimal("0.25")


def test_match_in_body_also_counted() -> None:
    score = compute_news_buy_bias(
        [
            NewsItem(
                title="Quarterly 10-Q filed",
                body="Buried in the filing: insider buying disclosed.",
            )
        ]
    )
    assert score.bullish_count == 1
    assert "insider buying" in score.matched_keywords


# ---- apply_buy_bias_to_confidence ------------------------------------


def test_zero_bias_returns_base_unchanged() -> None:
    boosted = apply_buy_bias_to_confidence(
        base_confidence_pct=Decimal("75"),
        buy_bias=Decimal("0"),
        max_boost_pct=Decimal("5"),
    )
    assert boosted == Decimal("75.00")


def test_full_bias_adds_max_boost() -> None:
    boosted = apply_buy_bias_to_confidence(
        base_confidence_pct=Decimal("75"),
        buy_bias=Decimal("1"),
        max_boost_pct=Decimal("5"),
    )
    assert boosted == Decimal("80.00")


def test_half_bias_adds_half_boost() -> None:
    boosted = apply_buy_bias_to_confidence(
        base_confidence_pct=Decimal("75"),
        buy_bias=Decimal("0.5"),
        max_boost_pct=Decimal("5"),
    )
    assert boosted == Decimal("77.50")


def test_clipped_at_100_pct() -> None:
    boosted = apply_buy_bias_to_confidence(
        base_confidence_pct=Decimal("98"),
        buy_bias=Decimal("1"),
        max_boost_pct=Decimal("5"),
    )
    assert boosted == Decimal("100")


def test_zero_max_boost_disables_feature() -> None:
    boosted = apply_buy_bias_to_confidence(
        base_confidence_pct=Decimal("75"),
        buy_bias=Decimal("1"),
        max_boost_pct=Decimal("0"),
    )
    assert boosted == Decimal("75.00")


def test_invalid_bias_rejected() -> None:
    with pytest.raises(ValueError):
        apply_buy_bias_to_confidence(
            base_confidence_pct=Decimal("75"),
            buy_bias=Decimal("-0.1"),
            max_boost_pct=Decimal("5"),
        )
    with pytest.raises(ValueError):
        apply_buy_bias_to_confidence(
            base_confidence_pct=Decimal("75"),
            buy_bias=Decimal("1.5"),
            max_boost_pct=Decimal("5"),
        )


def test_negative_max_boost_rejected() -> None:
    with pytest.raises(ValueError):
        apply_buy_bias_to_confidence(
            base_confidence_pct=Decimal("75"),
            buy_bias=Decimal("0.5"),
            max_boost_pct=Decimal("-1"),
        )


def test_float_inputs_rejected() -> None:
    with pytest.raises(TypeError):
        apply_buy_bias_to_confidence(
            base_confidence_pct=75.0,  # type: ignore[arg-type]
            buy_bias=Decimal("0.5"),
            max_boost_pct=Decimal("5"),
        )
    with pytest.raises(TypeError):
        apply_buy_bias_to_confidence(
            base_confidence_pct=Decimal("75"),
            buy_bias=0.5,  # type: ignore[arg-type]
            max_boost_pct=Decimal("5"),
        )
