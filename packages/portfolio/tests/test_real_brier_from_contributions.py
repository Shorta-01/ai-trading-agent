"""Tests for V1.2 §D — real Brier scores in auto-weighting.

The new ``compute_brier_history_from_contributions`` reads stored
``(prob_gain − indicator)²`` values directly instead of the crude
four-bucket outcome-label mapping. The previous helper discarded the
full continuous resolution of Brier — a predictor that issued 0.51 and
was right scored the same as one that issued 0.99 and was right, but
true Brier puts 0.24 vs 0.0001 between them.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import (
    compute_brier_history_from_contributions,
)


class _Contribution:
    """Test double matching the protocol the helper consumes."""

    def __init__(
        self,
        *,
        model_code: str,
        brier_score: Decimal | None,
        realised_return_pct: Decimal | None,
        created_at: datetime,
    ) -> None:
        self.model_code = model_code
        self.brier_score = brier_score
        self.realised_return_pct = realised_return_pct
        self.created_at = created_at


def _c(
    model: str,
    brier: float | None,
    *,
    realised: float | None = 1.0,
    days_ago: int = 1,
) -> _Contribution:
    return _Contribution(
        model_code=model,
        brier_score=Decimal(str(brier)) if brier is not None else None,
        realised_return_pct=(
            Decimal(str(realised)) if realised is not None else None
        ),
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
    )


# ---- Empty / no-data cases -----------------------------------------------


def test_empty_iterable_returns_empty_dict() -> None:
    assert compute_brier_history_from_contributions(contributions=[]) == {}


def test_contributions_without_brier_or_realised_are_skipped() -> None:
    """Rows with NULL brier_score (no realised outcome yet, or row
    written before the column existed) or NULL realised_return_pct
    contribute no signal — they must NOT count toward the mean."""

    rows = [
        _c("gbm", None, realised=1.0),
        _c("gbm", 0.2, realised=None),
    ]
    assert compute_brier_history_from_contributions(contributions=rows) == {}


# ---- True-Brier mean over the sample-size floor --------------------------


def test_mean_of_stored_brier_with_enough_samples() -> None:
    """Five contributions per model, mean is exact average."""

    rows = [
        _c("gbm", 0.10),
        _c("gbm", 0.20),
        _c("gbm", 0.30),
        _c("gbm", 0.40),
        _c("gbm", 0.50),
    ]
    out = compute_brier_history_from_contributions(contributions=rows)
    assert out == {"gbm": Decimal("0.300000")}


def test_predictor_below_sample_size_floor_is_omitted() -> None:
    """The sample-size floor is the safety net: weighting a predictor
    by the inverse of an unstable mean is worse than equal-weighting."""

    rows = [
        # 4 gbm rows, below the default min_sample_size=5
        _c("gbm", 0.20),
        _c("gbm", 0.20),
        _c("gbm", 0.20),
        _c("gbm", 0.20),
        # 6 momentum rows, above the floor
        *[_c("momentum", 0.30) for _ in range(6)],
    ]
    out = compute_brier_history_from_contributions(contributions=rows)
    assert "gbm" not in out
    assert out["momentum"] == Decimal("0.300000")


def test_min_sample_size_overrideable() -> None:
    """Operator can lower the floor (e.g. for sparse universes) — the
    default 5 is a practitioner choice, not a hard rule."""

    rows = [_c("gbm", 0.25) for _ in range(2)]
    out = compute_brier_history_from_contributions(
        contributions=rows, min_sample_size=2
    )
    assert out == {"gbm": Decimal("0.250000")}


# ---- Cutoff window --------------------------------------------------------


def test_cutoff_filters_out_old_contributions() -> None:
    """Only contributions created at-or-after the cutoff are scored."""

    cutoff = datetime.now(UTC) - timedelta(days=30)
    rows = [
        # Old rows — outside the window, ignored.
        _c("gbm", 0.99, days_ago=60),
        _c("gbm", 0.99, days_ago=50),
        _c("gbm", 0.99, days_ago=40),
        # Recent rows — inside the window, scored.
        _c("gbm", 0.10, days_ago=20),
        _c("gbm", 0.10, days_ago=10),
        _c("gbm", 0.10, days_ago=5),
        _c("gbm", 0.10, days_ago=3),
        _c("gbm", 0.10, days_ago=1),
    ]
    out = compute_brier_history_from_contributions(
        contributions=rows, cutoff_at=cutoff
    )
    # If old rows leaked in: mean ≈ (3*0.99 + 5*0.10) / 8 ≈ 0.434
    # With cutoff applied: mean of 5 recent rows = 0.10 exactly.
    assert out == {"gbm": Decimal("0.100000")}


def test_no_cutoff_includes_all_contributions() -> None:
    """``cutoff_at=None`` is the default and must include every row."""

    rows = [_c("gbm", 0.1) for _ in range(3)] + [
        _c("gbm", 0.5) for _ in range(3)
    ]
    out = compute_brier_history_from_contributions(contributions=rows)
    assert out == {"gbm": Decimal("0.300000")}


# ---- Per-model independence ----------------------------------------------


def test_separate_means_per_model_code() -> None:
    """Means are per ``model_code``; predictors don't pollute each
    other's averages."""

    rows = [
        *[_c("gbm", 0.1) for _ in range(5)],
        *[_c("momentum", 0.5) for _ in range(5)],
        *[_c("mean_reversion", 0.3) for _ in range(5)],
    ]
    out = compute_brier_history_from_contributions(contributions=rows)
    assert out == {
        "gbm": Decimal("0.100000"),
        "momentum": Decimal("0.500000"),
        "mean_reversion": Decimal("0.300000"),
    }


def test_one_predictor_above_floor_others_below_only_first_returned() -> None:
    rows = [
        *[_c("gbm", 0.2) for _ in range(8)],
        *[_c("momentum", 0.4) for _ in range(3)],
    ]
    out = compute_brier_history_from_contributions(contributions=rows)
    assert "gbm" in out
    assert "momentum" not in out


# ---- The information-preservation contract -------------------------------


def test_distinguishes_lucky_from_confident_unlike_old_mapping() -> None:
    """The whole point: a predictor that issued ``prob_gain = 0.51``
    and was right has Brier ≈ 0.24, while one that issued
    ``prob_gain = 0.99`` and was right has Brier ≈ 0.0001. The old
    label-bucket mapping collapsed both to 0.0; the new path preserves
    the distinction.
    """

    lucky = [_c("lucky_predictor", 0.2401) for _ in range(5)]  # (0.51-1)^2
    confident = [
        _c("confident_predictor", 0.0001) for _ in range(5)
    ]  # (0.99-1)^2
    out = compute_brier_history_from_contributions(
        contributions=lucky + confident
    )
    # Lower Brier = better. Confident must materially out-score lucky.
    assert out["confident_predictor"] < out["lucky_predictor"]
    # And the spread is meaningful — at least 0.2 apart.
    assert out["lucky_predictor"] - out["confident_predictor"] >= Decimal("0.2")


def test_six_decimal_quantization_matches_storage_round_trip() -> None:
    """The returned values must quantize to 6 decimals so a round-trip
    through the storage layer (Numeric(20, 6)) is exact."""

    rows = [_c("gbm", 0.1234567891) for _ in range(5)]
    out = compute_brier_history_from_contributions(contributions=rows)
    # Quantized to 6 decimals: 0.123457 (rounding).
    assert out["gbm"] == Decimal("0.123457")
