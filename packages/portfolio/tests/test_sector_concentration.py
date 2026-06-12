"""Tests for the sector concentration limit (V1.2 §L)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_INVALID_BUDGET,
    BLOCKING_REASON_INVALID_CANDIDATE_EUR,
    BLOCKING_REASON_INVALID_MAX_PCT,
    BLOCKING_REASON_SECTOR_CONCENTRATION_EXCEEDED,
    UNKNOWN_SECTOR,
    SectorAllocation,
    evaluate_sector_concentration,
)


def _alloc(sector: str, eur: str) -> SectorAllocation:
    return SectorAllocation(sector=sector, current_eur=Decimal(eur))


# ---- happy paths -----------------------------------------------------


def test_empty_portfolio_first_position_passes() -> None:
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("100000"),
        existing_allocations=[],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert result.allowed
    assert result.candidate_sector == "technology"
    assert result.current_sector_pct == Decimal("0.00")
    assert result.projected_sector_pct == Decimal("10.00")


def test_room_in_sector_passes() -> None:
    # Tech already at 15 %, adding another 5 % → 20 %, still under 25.
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("50000"),
        existing_allocations=[_alloc("technology", "150000")],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert result.allowed
    assert result.current_sector_pct == Decimal("15.00")
    assert result.projected_sector_pct == Decimal("20.00")


def test_other_sector_does_not_count_against_candidate() -> None:
    # Lots of healthcare, none in tech. New tech position passes.
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("100000"),
        existing_allocations=[_alloc("healthcare", "240000")],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert result.allowed
    assert result.current_sector_pct == Decimal("0.00")


# ---- exceeds cap -----------------------------------------------------


def test_exceeds_cap_blocked() -> None:
    # Tech at 22 %, adding another 5 % → 27 %, breaches 25.
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("50000"),
        existing_allocations=[_alloc("technology", "220000")],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_SECTOR_CONCENTRATION_EXCEEDED
    assert result.current_sector_pct == Decimal("22.00")
    assert result.projected_sector_pct == Decimal("27.00")
    assert result.max_allowed_pct == Decimal("25")


def test_exactly_at_cap_passes() -> None:
    # Doctrine: > cap blocks; == cap is allowed.
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("50000"),
        existing_allocations=[_alloc("technology", "200000")],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert result.allowed
    assert result.projected_sector_pct == Decimal("25.00")


def test_first_position_oversized_blocks() -> None:
    # Empty portfolio, but the requested EUR alone exceeds the cap.
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("300000"),
        existing_allocations=[],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_SECTOR_CONCENTRATION_EXCEEDED
    assert result.projected_sector_pct == Decimal("30.00")


# ---- aggregation -----------------------------------------------------


def test_multiple_entries_same_sector_summed() -> None:
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("60000"),
        existing_allocations=[
            _alloc("technology", "100000"),
            _alloc("technology", "100000"),
        ],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    # 200K + 60K = 260K = 26 % → blocked.
    assert not result.allowed
    assert result.current_sector_pct == Decimal("20.00")
    assert result.projected_sector_pct == Decimal("26.00")


def test_case_insensitive_sector_matching() -> None:
    # "Technology" should match "technology" allocation.
    result = evaluate_sector_concentration(
        candidate_sector="Technology",
        candidate_intended_eur=Decimal("60000"),
        existing_allocations=[_alloc("technology", "200000")],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert result.candidate_sector == "technology"
    assert result.current_sector_pct == Decimal("20.00")


# ---- unknown sector --------------------------------------------------


def test_none_sector_bucketed_as_unknown() -> None:
    result = evaluate_sector_concentration(
        candidate_sector=None,
        candidate_intended_eur=Decimal("100000"),
        existing_allocations=[],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert result.candidate_sector == UNKNOWN_SECTOR
    assert result.allowed


def test_empty_string_sector_bucketed_as_unknown() -> None:
    result = evaluate_sector_concentration(
        candidate_sector="   ",
        candidate_intended_eur=Decimal("100000"),
        existing_allocations=[],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert result.candidate_sector == UNKNOWN_SECTOR


def test_unknown_sector_counts_toward_its_own_cap() -> None:
    # Two unknown-sector positions already at 22 %; new unknown 5 %
    # pushes over 25 %.
    result = evaluate_sector_concentration(
        candidate_sector=None,
        candidate_intended_eur=Decimal("50000"),
        existing_allocations=[
            _alloc("", "100000"),
            _alloc(None, "120000"),  # type: ignore[arg-type]
        ],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_SECTOR_CONCENTRATION_EXCEEDED
    assert result.candidate_sector == UNKNOWN_SECTOR


# ---- invalid inputs --------------------------------------------------


def test_zero_budget_blocked() -> None:
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("100000"),
        existing_allocations=[],
        total_budget_eur=Decimal("0"),
        max_sector_pct=Decimal("25"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_BUDGET


def test_negative_max_pct_blocked() -> None:
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("100000"),
        existing_allocations=[],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("-5"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_MAX_PCT


def test_above_100_max_pct_blocked() -> None:
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("100000"),
        existing_allocations=[],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("150"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_MAX_PCT


def test_negative_candidate_eur_blocked() -> None:
    result = evaluate_sector_concentration(
        candidate_sector="technology",
        candidate_intended_eur=Decimal("-1"),
        existing_allocations=[],
        total_budget_eur=Decimal("1000000"),
        max_sector_pct=Decimal("25"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_CANDIDATE_EUR


def test_float_inputs_rejected() -> None:
    with pytest.raises(TypeError):
        evaluate_sector_concentration(
            candidate_sector="technology",
            candidate_intended_eur=100000.0,  # type: ignore[arg-type]
            existing_allocations=[],
            total_budget_eur=Decimal("1000000"),
            max_sector_pct=Decimal("25"),
        )
    with pytest.raises(TypeError):
        evaluate_sector_concentration(
            candidate_sector="technology",
            candidate_intended_eur=Decimal("100000"),
            existing_allocations=[],
            total_budget_eur=1000000.0,  # type: ignore[arg-type]
            max_sector_pct=Decimal("25"),
        )
    with pytest.raises(TypeError):
        evaluate_sector_concentration(
            candidate_sector="technology",
            candidate_intended_eur=Decimal("100000"),
            existing_allocations=[],
            total_budget_eur=Decimal("1000000"),
            max_sector_pct=25.0,  # type: ignore[arg-type]
        )
