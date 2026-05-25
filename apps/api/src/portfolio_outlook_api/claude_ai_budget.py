"""Anthropic Claude monthly budget enforcement (V1.1 Slice 29).

The §22.2 lock caps real Anthropic Claude usage at
``CLAUDE_AI_BUDGET_MONTHLY_EUR`` (default €50). This module owns the
read/write surface against the ``claude_ai_budget_usage`` audit table
created by storage migration 0043. The real provider checks
:func:`monthly_budget_status` before each call; if the running total
already exceeds the cap, the provider raises
:class:`ClaudeAiBudgetExceededError` and the orchestrator falls back
to the stub.

Pricing — V1.1 §22.2 default rates (€ per million units):

* Claude Haiku 4.5 — input €0.80 / cached €0.08 / output €4.00
* Claude Sonnet 4.6 — input €3.00 / cached €0.30 / output €15.00

These are conservative ceilings (Anthropic prices in USD with frequent
discounts); the operator can override via env if needed. The module
intentionally avoids hard-coding live Anthropic SDK price strings —
those drift and the cap is what matters for the safety doctrine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final, Protocol
from uuid import uuid4

from ai_trading_agent_storage import ClaudeAiBudgetUsageRecord

# Default EUR-per-million-units rates. Overridable via constructor.
DEFAULT_INPUT_EUR_PER_M: Final[Decimal] = Decimal("0.80")
DEFAULT_CACHED_INPUT_EUR_PER_M: Final[Decimal] = Decimal("0.08")
DEFAULT_OUTPUT_EUR_PER_M: Final[Decimal] = Decimal("4.00")


class ClaudeAiBudgetExceededError(RuntimeError):
    """Raised by the real provider when the monthly cap is hit."""


@dataclass(frozen=True)
class BudgetStatus:
    budget_month: str
    monthly_cap_eur: Decimal
    monthly_total_eur: Decimal
    remaining_eur: Decimal
    exceeded: bool


@dataclass(frozen=True)
class CallCostBreakdown:
    """Cost breakdown for one Anthropic call."""

    input_units: int
    cached_input_units: int
    output_units: int
    cost_eur: Decimal


class _BudgetRepoProtocol(Protocol):
    def monthly_total_eur(self, budget_month: str) -> Decimal: ...

    def save_usage(self, record: ClaudeAiBudgetUsageRecord) -> object: ...


def budget_month_of(now: datetime) -> str:
    """Format a ``datetime`` into the locked ``YYYY-MM`` month tag."""

    return now.astimezone(UTC).strftime("%Y-%m")


def compute_cost_eur(
    *,
    input_units: int,
    cached_input_units: int,
    output_units: int,
    input_eur_per_m: Decimal = DEFAULT_INPUT_EUR_PER_M,
    cached_input_eur_per_m: Decimal = DEFAULT_CACHED_INPUT_EUR_PER_M,
    output_eur_per_m: Decimal = DEFAULT_OUTPUT_EUR_PER_M,
) -> Decimal:
    """Translate a unit-count tuple into a EUR cost.

    All three input counters are non-negative; negative counters are
    rejected (a bug in the upstream SDK shouldn't sneak through into
    the audit row).
    """

    if input_units < 0 or cached_input_units < 0 or output_units < 0:
        raise ValueError("unit counts must be non-negative")
    million = Decimal("1000000")
    cost = (
        Decimal(input_units) * input_eur_per_m / million
        + Decimal(cached_input_units) * cached_input_eur_per_m / million
        + Decimal(output_units) * output_eur_per_m / million
    )
    return cost.quantize(Decimal("0.000001"))


def monthly_budget_status(
    *,
    repo: _BudgetRepoProtocol,
    monthly_cap_eur: Decimal,
    now: datetime | None = None,
) -> BudgetStatus:
    """Return the current month's running total + remaining headroom."""

    actual_now = now if now is not None else datetime.now(UTC)
    month = budget_month_of(actual_now)
    total = repo.monthly_total_eur(month)
    remaining = monthly_cap_eur - total
    return BudgetStatus(
        budget_month=month,
        monthly_cap_eur=monthly_cap_eur,
        monthly_total_eur=total,
        remaining_eur=remaining,
        exceeded=remaining <= Decimal("0"),
    )


def assert_budget_available(
    *,
    repo: _BudgetRepoProtocol,
    monthly_cap_eur: Decimal,
    now: datetime | None = None,
) -> BudgetStatus:
    """Raise :class:`ClaudeAiBudgetExceededError` when the cap is hit."""

    status = monthly_budget_status(
        repo=repo, monthly_cap_eur=monthly_cap_eur, now=now
    )
    if status.exceeded:
        raise ClaudeAiBudgetExceededError(
            f"Claude AI budget cap of €{monthly_cap_eur} reached for "
            f"{status.budget_month} (totaal €{status.monthly_total_eur:.2f}); "
            "provider valt terug op de stub."
        )
    return status


def persist_call_cost(
    *,
    repo: _BudgetRepoProtocol,
    provider_code: str,
    model_name: str,
    call_kind: str,
    breakdown: CallCostBreakdown,
    explanation_nl: str | None = None,
    now: datetime | None = None,
) -> ClaudeAiBudgetUsageRecord:
    """Save one audit row for the just-completed call. Returns the
    persisted record so callers can include the usage id in their
    response."""

    actual_now = now if now is not None else datetime.now(UTC)
    record = ClaudeAiBudgetUsageRecord(
        usage_id=f"clbu_{uuid4().hex}",
        budget_month=budget_month_of(actual_now),
        provider_code=provider_code,
        model_name=model_name,
        called_at=actual_now,
        input_units=breakdown.input_units,
        cached_input_units=breakdown.cached_input_units,
        output_units=breakdown.output_units,
        cost_eur=breakdown.cost_eur,
        call_kind=call_kind,
        explanation_nl=explanation_nl,
    )
    repo.save_usage(record)
    return record


__all__ = [
    "DEFAULT_CACHED_INPUT_EUR_PER_M",
    "DEFAULT_INPUT_EUR_PER_M",
    "DEFAULT_OUTPUT_EUR_PER_M",
    "BudgetStatus",
    "CallCostBreakdown",
    "ClaudeAiBudgetExceededError",
    "assert_budget_available",
    "budget_month_of",
    "compute_cost_eur",
    "monthly_budget_status",
    "persist_call_cost",
]
