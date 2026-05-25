"""Tests for the V1.1 Slice 29 Claude AI budget enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from ai_trading_agent_storage import ClaudeAiBudgetUsageRecord

from portfolio_outlook_api.claude_ai_budget import (
    BudgetStatus,
    CallCostBreakdown,
    ClaudeAiBudgetExceededError,
    assert_budget_available,
    budget_month_of,
    compute_cost_eur,
    monthly_budget_status,
    persist_call_cost,
)


class _FakeBudgetRepo:
    def __init__(self, *, totals: dict[str, Decimal] | None = None) -> None:
        self._totals = totals or {}
        self.saved: list[ClaudeAiBudgetUsageRecord] = []

    def monthly_total_eur(self, budget_month: str) -> Decimal:
        return self._totals.get(budget_month, Decimal("0"))

    def save_usage(self, record):  # type: ignore[no-untyped-def]
        self.saved.append(record)


# ---- compute_cost_eur ---------------------------------------------------


def test_compute_cost_eur_uses_default_per_million_rates() -> None:
    cost = compute_cost_eur(
        input_units=1_000_000,
        cached_input_units=0,
        output_units=0,
    )
    # 1M input units × €0.80/M = €0.80
    assert cost == Decimal("0.800000")


def test_compute_cost_eur_cached_is_cheaper() -> None:
    cost = compute_cost_eur(
        input_units=0,
        cached_input_units=1_000_000,
        output_units=0,
    )
    assert cost == Decimal("0.080000")


def test_compute_cost_eur_output_priced_high() -> None:
    cost = compute_cost_eur(
        input_units=0,
        cached_input_units=0,
        output_units=1_000_000,
    )
    assert cost == Decimal("4.000000")


def test_compute_cost_eur_rejects_negative_units() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        compute_cost_eur(
            input_units=-1, cached_input_units=0, output_units=0
        )


def test_compute_cost_eur_supports_custom_rates() -> None:
    cost = compute_cost_eur(
        input_units=1_000_000,
        cached_input_units=0,
        output_units=0,
        input_eur_per_m=Decimal("3.00"),
    )
    assert cost == Decimal("3.000000")


# ---- budget_month_of ----------------------------------------------------


def test_budget_month_of_formats_as_year_month() -> None:
    now = datetime(2026, 6, 17, 12, 30, tzinfo=UTC)
    assert budget_month_of(now) == "2026-06"


# ---- monthly_budget_status + assert_budget_available --------------------


def test_monthly_budget_status_returns_remaining_when_under_cap() -> None:
    repo = _FakeBudgetRepo(totals={"2026-06": Decimal("12.50")})
    status = monthly_budget_status(
        repo=repo,
        monthly_cap_eur=Decimal("50"),
        now=datetime(2026, 6, 17, tzinfo=UTC),
    )
    assert isinstance(status, BudgetStatus)
    assert status.budget_month == "2026-06"
    assert status.monthly_total_eur == Decimal("12.50")
    assert status.remaining_eur == Decimal("37.50")
    assert status.exceeded is False


def test_monthly_budget_status_flags_exceeded_when_total_meets_cap() -> None:
    repo = _FakeBudgetRepo(totals={"2026-06": Decimal("50.00")})
    status = monthly_budget_status(
        repo=repo,
        monthly_cap_eur=Decimal("50"),
        now=datetime(2026, 6, 17, tzinfo=UTC),
    )
    assert status.exceeded is True


def test_assert_budget_available_raises_when_cap_hit() -> None:
    repo = _FakeBudgetRepo(totals={"2026-06": Decimal("51.00")})
    with pytest.raises(ClaudeAiBudgetExceededError, match="2026-06"):
        assert_budget_available(
            repo=repo,
            monthly_cap_eur=Decimal("50"),
            now=datetime(2026, 6, 17, tzinfo=UTC),
        )


def test_assert_budget_available_passes_when_under_cap() -> None:
    repo = _FakeBudgetRepo(totals={"2026-06": Decimal("10.00")})
    status = assert_budget_available(
        repo=repo,
        monthly_cap_eur=Decimal("50"),
        now=datetime(2026, 6, 17, tzinfo=UTC),
    )
    assert status.exceeded is False


# ---- persist_call_cost --------------------------------------------------


def test_persist_call_cost_saves_audit_row_with_safety_booleans_false() -> None:
    repo = _FakeBudgetRepo()
    breakdown = CallCostBreakdown(
        input_units=1000,
        cached_input_units=500,
        output_units=200,
        cost_eur=Decimal("0.001640"),
    )
    record = persist_call_cost(
        repo=repo,
        provider_code="anthropic_claude",
        model_name="claude-haiku-4-5-20251001",
        call_kind="explanation",
        breakdown=breakdown,
        explanation_nl="test call",
        now=datetime(2026, 6, 17, 9, 0, tzinfo=UTC),
    )
    assert record.budget_month == "2026-06"
    assert record.input_units == 1000
    assert record.cached_input_units == 500
    assert record.output_units == 200
    assert record.cost_eur == Decimal("0.001640")
    assert record.safe_for_action_drafts is False
    assert record.safe_for_orders is False
    assert len(repo.saved) == 1
    assert repo.saved[0] is record


def test_persist_call_cost_rejects_unknown_call_kind() -> None:
    repo = _FakeBudgetRepo()
    breakdown = CallCostBreakdown(
        input_units=0,
        cached_input_units=0,
        output_units=0,
        cost_eur=Decimal("0"),
    )
    with pytest.raises(ValueError, match="call_kind"):
        persist_call_cost(
            repo=repo,
            provider_code="anthropic_claude",
            model_name="claude-haiku",
            call_kind="bogus",
            breakdown=breakdown,
        )
