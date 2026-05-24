"""Deterministic daily briefing builder (Slice 12).

Given the typed inputs (positions, suggestions, drafts, diary entries,
events) the V1 doctrine requires a once-per-day Dutch summary that
references only locked numbers and counts. AI **never** authors the
briefing.

This module is pure Python: no I/O, no datetime.now(), no provider
calls. The caller supplies a ``now`` and a ``lookback_started_at``
cutoff so the counters are reproducible.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

ALERT_KIND_NEW_SUGGESTION = "new_suggestion"
ALERT_KIND_NEW_DECISION_PACKAGE = "new_decision_package"
ALERT_KIND_NEW_ACTION_DRAFT = "new_action_draft"
ALERT_KIND_DIARY_OUTCOME_CLOSED = "diary_outcome_closed"
ALERT_KIND_CRITICAL_DRAFT_EVENT = "critical_draft_event"
ALERT_KIND_FX_STALE = "fx_stale"

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

STATUS_READY = "ready"
STATUS_BLOCKED = "blocked"


@dataclass(frozen=True)
class BriefingPositionInput:
    symbol: str
    conid: str | None
    quantity: Decimal
    market_value_base_currency: Decimal | None


@dataclass(frozen=True)
class BriefingSuggestionInput:
    suggestion_id: str
    symbol: str
    action_label_nl: str
    generated_at: datetime
    status: str


@dataclass(frozen=True)
class BriefingDecisionPackageInput:
    decision_package_id: str
    symbol: str
    generated_at: datetime
    status: str


@dataclass(frozen=True)
class BriefingActionDraftInput:
    draft_id: str
    symbol: str
    action_side: str
    created_at: datetime
    dry_run_status: str


@dataclass(frozen=True)
class BriefingDiaryOutcomeInput:
    suggestion_id: str
    symbol: str
    last_evaluated_at: datetime
    outcome_label_1m: str | None


@dataclass(frozen=True)
class BriefingCriticalEventInput:
    event_id: str
    draft_id: str
    event_type: str
    to_state: str | None
    occurred_at: datetime


@dataclass(frozen=True)
class BriefingInputs:
    now: datetime
    lookback_started_at: datetime
    base_currency: str | None
    fx_freshness_status: str | None
    cash_total_base_currency: Decimal | None
    positions: tuple[BriefingPositionInput, ...] = ()
    suggestions: tuple[BriefingSuggestionInput, ...] = ()
    decision_packages: tuple[BriefingDecisionPackageInput, ...] = ()
    action_drafts: tuple[BriefingActionDraftInput, ...] = ()
    diary_outcomes: tuple[BriefingDiaryOutcomeInput, ...] = ()
    critical_events: tuple[BriefingCriticalEventInput, ...] = ()


@dataclass(frozen=True)
class BriefingAlertResult:
    alert_kind: str
    severity: str
    reference_kind: str | None
    reference_id: str | None
    title_nl: str
    body_nl: str


@dataclass(frozen=True)
class BriefingResult:
    briefing_date: date
    position_count: int
    total_position_value: Decimal | None
    new_suggestion_count: int
    new_decision_package_count: int
    new_action_draft_count: int
    diary_outcomes_closed_count: int
    critical_event_count: int
    alerts: tuple[BriefingAlertResult, ...] = field(default_factory=tuple)
    summary_nl: str = ""
    help_nl: str = ""
    status: str = STATUS_READY
    blocking_reason: str | None = None


def _sum_position_value(
    positions: Iterable[BriefingPositionInput],
) -> Decimal | None:
    values = [
        p.market_value_base_currency
        for p in positions
        if p.market_value_base_currency is not None
    ]
    if not values:
        return None
    total = Decimal("0")
    for value in values:
        total += value
    return total


def _filter_after[T](items: Iterable[T], attr: str, cutoff: datetime) -> list[T]:
    return [item for item in items if getattr(item, attr) >= cutoff]


def _build_alerts(
    *,
    inputs: BriefingInputs,
    new_suggestions: list[BriefingSuggestionInput],
    new_packages: list[BriefingDecisionPackageInput],
    new_drafts: list[BriefingActionDraftInput],
    closed_outcomes: list[BriefingDiaryOutcomeInput],
    critical_events: list[BriefingCriticalEventInput],
) -> list[BriefingAlertResult]:
    alerts: list[BriefingAlertResult] = []
    for suggestion in new_suggestions:
        alerts.append(
            BriefingAlertResult(
                alert_kind=ALERT_KIND_NEW_SUGGESTION,
                severity=SEVERITY_INFO,
                reference_kind="suggestion",
                reference_id=suggestion.suggestion_id,
                title_nl=f"Nieuwe suggestie: {suggestion.symbol} → {suggestion.action_label_nl}",
                body_nl=(
                    f"Een nieuwe suggestie voor {suggestion.symbol} met status "
                    f"{suggestion.status}. Lees de Decision Package voor de evidence."
                ),
            )
        )
    for package in new_packages:
        alerts.append(
            BriefingAlertResult(
                alert_kind=ALERT_KIND_NEW_DECISION_PACKAGE,
                severity=SEVERITY_INFO,
                reference_kind="decision_package",
                reference_id=package.decision_package_id,
                title_nl=f"Nieuwe Decision Package: {package.symbol}",
                body_nl=(
                    f"Decision Package voor {package.symbol} is opgesteld "
                    f"(status: {package.status})."
                ),
            )
        )
    for draft in new_drafts:
        severity = (
            SEVERITY_WARNING if draft.dry_run_status == "failed" else SEVERITY_INFO
        )
        alerts.append(
            BriefingAlertResult(
                alert_kind=ALERT_KIND_NEW_ACTION_DRAFT,
                severity=severity,
                reference_kind="action_draft",
                reference_id=draft.draft_id,
                title_nl=(
                    f"Nieuwe action draft: {draft.action_side} {draft.symbol}"
                ),
                body_nl=(
                    f"Action draft voor {draft.symbol} ({draft.action_side}) "
                    f"met dry-run status {draft.dry_run_status}."
                ),
            )
        )
    for outcome in closed_outcomes:
        if outcome.outcome_label_1m is None:
            continue
        alerts.append(
            BriefingAlertResult(
                alert_kind=ALERT_KIND_DIARY_OUTCOME_CLOSED,
                severity=SEVERITY_INFO,
                reference_kind="diary_entry",
                reference_id=outcome.suggestion_id,
                title_nl=(
                    f"Prediction-diary outcome: {outcome.symbol} → "
                    f"{outcome.outcome_label_1m}"
                ),
                body_nl=(
                    f"De 1-maand outcome voor {outcome.symbol} is geëvalueerd als "
                    f"{outcome.outcome_label_1m}."
                ),
            )
        )
    for event in critical_events:
        alerts.append(
            BriefingAlertResult(
                alert_kind=ALERT_KIND_CRITICAL_DRAFT_EVENT,
                severity=SEVERITY_CRITICAL,
                reference_kind="action_draft_event",
                reference_id=event.event_id,
                title_nl=(
                    f"Critical state event: draft {event.draft_id} → "
                    f"{event.to_state or event.event_type}"
                ),
                body_nl=(
                    f"Event {event.event_type} op draft {event.draft_id}; "
                    "lees de audit-log voor details."
                ),
            )
        )
    if inputs.fx_freshness_status and inputs.fx_freshness_status.lower() == "stale":
        alerts.append(
            BriefingAlertResult(
                alert_kind=ALERT_KIND_FX_STALE,
                severity=SEVERITY_WARNING,
                reference_kind="fx_freshness",
                reference_id=None,
                title_nl="FX-koersen zijn stale",
                body_nl=(
                    "De laatste FX-snapshot is niet vers; portfolio-waarderingen "
                    "kunnen afwijken. Voer een market-data sync uit."
                ),
            )
        )
    return alerts


def _build_summary_nl(
    *,
    position_count: int,
    total_position_value: Decimal | None,
    base_currency: str | None,
    cash_total: Decimal | None,
    fx_freshness: str | None,
    new_suggestion_count: int,
    new_decision_package_count: int,
    new_action_draft_count: int,
    diary_outcomes_closed_count: int,
    critical_event_count: int,
) -> str:
    parts: list[str] = []
    if position_count == 0:
        parts.append("Geen open posities vandaag.")
    else:
        total_text = (
            f"; totale waardering {base_currency} {total_position_value}"
            if total_position_value is not None and base_currency
            else ""
        )
        parts.append(f"Je houdt {position_count} positie(s){total_text}.")
    if cash_total is not None and base_currency:
        parts.append(f"Cash op rekening: {base_currency} {cash_total}.")
    if fx_freshness:
        parts.append(f"FX-versheid: {fx_freshness}.")
    new_items = (
        new_suggestion_count
        + new_decision_package_count
        + new_action_draft_count
    )
    if new_items == 0:
        parts.append("Geen nieuwe suggesties, packages of drafts sinds gisteren.")
    else:
        parts.append(
            f"Nieuw sinds vorige briefing: {new_suggestion_count} suggestie(s), "
            f"{new_decision_package_count} Decision Package(s), "
            f"{new_action_draft_count} action draft(s)."
        )
    if diary_outcomes_closed_count > 0:
        parts.append(
            f"{diary_outcomes_closed_count} prediction-diary outcome(s) "
            "afgesloten."
        )
    if critical_event_count > 0:
        parts.append(
            f"{critical_event_count} critical state event(s) — controleer de "
            "audit log."
        )
    return " ".join(parts)


def compute_daily_briefing(inputs: BriefingInputs) -> BriefingResult:
    """Build the deterministic daily briefing.

    Counts are derived from the typed inputs filtered by
    ``lookback_started_at``. The Dutch summary is built from those
    counts and the locked portfolio numbers; AI is never invoked.
    """

    cutoff = inputs.lookback_started_at
    new_suggestions = _filter_after(inputs.suggestions, "generated_at", cutoff)
    new_packages = _filter_after(inputs.decision_packages, "generated_at", cutoff)
    new_drafts = _filter_after(inputs.action_drafts, "created_at", cutoff)
    closed_outcomes = _filter_after(
        inputs.diary_outcomes, "last_evaluated_at", cutoff
    )
    critical_events = _filter_after(
        inputs.critical_events, "occurred_at", cutoff
    )

    position_count = len(inputs.positions)
    total_position_value = _sum_position_value(inputs.positions)

    alerts = _build_alerts(
        inputs=inputs,
        new_suggestions=new_suggestions,
        new_packages=new_packages,
        new_drafts=new_drafts,
        closed_outcomes=closed_outcomes,
        critical_events=critical_events,
    )
    summary = _build_summary_nl(
        position_count=position_count,
        total_position_value=total_position_value,
        base_currency=inputs.base_currency,
        cash_total=inputs.cash_total_base_currency,
        fx_freshness=inputs.fx_freshness_status,
        new_suggestion_count=len(new_suggestions),
        new_decision_package_count=len(new_packages),
        new_action_draft_count=len(new_drafts),
        diary_outcomes_closed_count=len(closed_outcomes),
        critical_event_count=len(critical_events),
    )
    help_nl = (
        "Briefings zijn deterministisch en samengesteld uit reeds opgeslagen "
        "evidence. AI schrijft geen briefings; geen auto-execution."
    )

    return BriefingResult(
        briefing_date=inputs.now.date(),
        position_count=position_count,
        total_position_value=total_position_value,
        new_suggestion_count=len(new_suggestions),
        new_decision_package_count=len(new_packages),
        new_action_draft_count=len(new_drafts),
        diary_outcomes_closed_count=len(closed_outcomes),
        critical_event_count=len(critical_events),
        alerts=tuple(alerts),
        summary_nl=summary,
        help_nl=help_nl,
        status=STATUS_READY,
        blocking_reason=None,
    )


__all__ = [
    "ALERT_KIND_NEW_SUGGESTION",
    "ALERT_KIND_NEW_DECISION_PACKAGE",
    "ALERT_KIND_NEW_ACTION_DRAFT",
    "ALERT_KIND_DIARY_OUTCOME_CLOSED",
    "ALERT_KIND_CRITICAL_DRAFT_EVENT",
    "ALERT_KIND_FX_STALE",
    "SEVERITY_INFO",
    "SEVERITY_WARNING",
    "SEVERITY_CRITICAL",
    "STATUS_READY",
    "STATUS_BLOCKED",
    "BriefingPositionInput",
    "BriefingSuggestionInput",
    "BriefingDecisionPackageInput",
    "BriefingActionDraftInput",
    "BriefingDiaryOutcomeInput",
    "BriefingCriticalEventInput",
    "BriefingInputs",
    "BriefingAlertResult",
    "BriefingResult",
    "compute_daily_briefing",
]
