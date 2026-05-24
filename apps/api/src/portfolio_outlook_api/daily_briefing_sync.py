"""Daily briefing orchestrator (Slice 12).

Reads the persisted positions / suggestions / Decision Packages / action
drafts / prediction-diary entries / draft-events that fall after the
lookback cutoff, calls the deterministic
:func:`compute_daily_briefing`, and persists the resulting summary +
alerts.

No I/O outside the repositories. AI never authors the briefing.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetActionDraftEventRecord,
    AssetActionDraftRecord,
    AssetDecisionPackageRecord,
    AssetSuggestionRecord,
    BriefingAlertRecord,
    DailyBriefingRecord,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    PredictionDiaryEntryRecord,
)
from portfolio_outlook_portfolio import (
    BriefingActionDraftInput,
    BriefingCriticalEventInput,
    BriefingDecisionPackageInput,
    BriefingDiaryOutcomeInput,
    BriefingInputs,
    BriefingPositionInput,
    BriefingSuggestionInput,
    compute_daily_briefing,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailyBriefingReport:
    requested_at: datetime
    completed_at: datetime
    status: str
    status_nl: str
    help_nl: str
    briefing_id: str | None
    alert_count: int


class _BriefingRepoProtocol(Protocol):
    def upsert_daily_briefing(
        self, record: DailyBriefingRecord
    ) -> object: ...

    def save_briefing_alert(
        self, record: BriefingAlertRecord
    ) -> object: ...

    def delete_alerts_for_briefing(self, briefing_id: str) -> object: ...


def _to_position_inputs(
    positions: Iterable[IbkrPositionSnapshotRecord],
) -> tuple[BriefingPositionInput, ...]:
    return tuple(
        BriefingPositionInput(
            symbol=p.symbol,
            conid=p.conid,
            quantity=p.quantity,
            market_value_base_currency=None,
        )
        for p in positions
    )


def _to_suggestion_inputs(
    suggestions: Iterable[AssetSuggestionRecord],
) -> tuple[BriefingSuggestionInput, ...]:
    return tuple(
        BriefingSuggestionInput(
            suggestion_id=s.suggestion_id,
            symbol=s.symbol,
            action_label_nl=s.action_label_nl,
            generated_at=s.generated_at,
            status=s.status,
        )
        for s in suggestions
    )


def _to_package_inputs(
    packages: Iterable[AssetDecisionPackageRecord],
) -> tuple[BriefingDecisionPackageInput, ...]:
    return tuple(
        BriefingDecisionPackageInput(
            decision_package_id=p.decision_package_id,
            symbol=p.symbol,
            generated_at=p.generated_at,
            status=p.status,
        )
        for p in packages
    )


def _to_draft_inputs(
    drafts: Iterable[AssetActionDraftRecord],
) -> tuple[BriefingActionDraftInput, ...]:
    return tuple(
        BriefingActionDraftInput(
            draft_id=d.draft_id,
            symbol=d.symbol,
            action_side=d.action_side,
            created_at=d.created_at,
            dry_run_status=d.dry_run_status,
        )
        for d in drafts
    )


def _to_diary_inputs(
    diary_entries: Iterable[PredictionDiaryEntryRecord],
) -> tuple[BriefingDiaryOutcomeInput, ...]:
    return tuple(
        BriefingDiaryOutcomeInput(
            suggestion_id=d.suggestion_id,
            symbol=d.symbol,
            last_evaluated_at=d.last_evaluated_at,
            outcome_label_1m=d.outcome_label_1m,
        )
        for d in diary_entries
    )


def _to_event_inputs(
    events: Iterable[AssetActionDraftEventRecord],
) -> tuple[BriefingCriticalEventInput, ...]:
    return tuple(
        BriefingCriticalEventInput(
            event_id=e.event_id,
            draft_id=e.draft_id,
            event_type=e.event_type,
            to_state=e.to_state,
            occurred_at=e.occurred_at,
        )
        for e in events
        if e.severity == "critical"
    )


def _sum_cash(
    cash_snapshots: Iterable[IbkrAccountCashSnapshotRecord],
) -> Decimal | None:
    values = [c.cash for c in cash_snapshots if c.cash is not None]
    if not values:
        return None
    total = Decimal("0")
    for value in values:
        total += value
    return total


def generate_daily_briefing(
    *,
    positions: Iterable[IbkrPositionSnapshotRecord],
    cash_snapshots: Iterable[IbkrAccountCashSnapshotRecord],
    suggestions: Iterable[AssetSuggestionRecord],
    decision_packages: Iterable[AssetDecisionPackageRecord],
    action_drafts: Iterable[AssetActionDraftRecord],
    diary_entries: Iterable[PredictionDiaryEntryRecord],
    critical_events: Iterable[AssetActionDraftEventRecord],
    base_currency: str | None,
    fx_freshness_status: str | None,
    lookback_hours: int,
    repo: _BriefingRepoProtocol,
    now: datetime | None = None,
) -> DailyBriefingReport:
    """Build and persist one daily briefing.

    ``now`` is injectable to keep tests deterministic; in production the
    route passes ``datetime.now(UTC)``.
    """

    requested_at = datetime.now(UTC)
    actual_now = now or requested_at
    lookback_started_at = actual_now - timedelta(hours=lookback_hours)

    inputs = BriefingInputs(
        now=actual_now,
        lookback_started_at=lookback_started_at,
        base_currency=base_currency,
        fx_freshness_status=fx_freshness_status,
        cash_total_base_currency=_sum_cash(cash_snapshots),
        positions=_to_position_inputs(positions),
        suggestions=_to_suggestion_inputs(suggestions),
        decision_packages=_to_package_inputs(decision_packages),
        action_drafts=_to_draft_inputs(action_drafts),
        diary_outcomes=_to_diary_inputs(diary_entries),
        critical_events=_to_event_inputs(critical_events),
    )
    result = compute_daily_briefing(inputs)

    briefing_id = f"brief_{uuid4().hex}"
    briefing = DailyBriefingRecord(
        briefing_id=briefing_id,
        briefing_date=result.briefing_date,
        generated_at=actual_now,
        lookback_started_at=lookback_started_at,
        position_count=result.position_count,
        base_currency=base_currency,
        total_position_value=result.total_position_value,
        cash_total=inputs.cash_total_base_currency,
        fx_freshness_status=fx_freshness_status,
        new_suggestion_count=result.new_suggestion_count,
        new_decision_package_count=result.new_decision_package_count,
        new_action_draft_count=result.new_action_draft_count,
        diary_outcomes_closed_count=result.diary_outcomes_closed_count,
        critical_event_count=result.critical_event_count,
        alert_count=len(result.alerts),
        summary_nl=result.summary_nl,
        help_nl=result.help_nl,
        status=result.status,
        blocking_reason=result.blocking_reason,
    )

    try:
        repo.upsert_daily_briefing(briefing)
        repo.delete_alerts_for_briefing(briefing_id)
        for alert in result.alerts:
            repo.save_briefing_alert(
                BriefingAlertRecord(
                    alert_id=f"alrt_{uuid4().hex}",
                    briefing_id=briefing_id,
                    alert_kind=alert.alert_kind,
                    severity=alert.severity,
                    reference_kind=alert.reference_kind,
                    reference_id=alert.reference_id,
                    title_nl=alert.title_nl,
                    body_nl=alert.body_nl,
                    acknowledged_at=None,
                    linked_at=actual_now,
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("daily briefing persistence failed")
        return DailyBriefingReport(
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
            status="failed",
            status_nl="Dagbriefing kon niet worden opgeslagen",
            help_nl=f"De opslag gaf een fout: {exc}",
            briefing_id=None,
            alert_count=0,
        )

    return DailyBriefingReport(
        requested_at=requested_at,
        completed_at=datetime.now(UTC),
        status=result.status,
        status_nl="Dagbriefing opgeslagen",
        help_nl=result.help_nl,
        briefing_id=briefing_id,
        alert_count=len(result.alerts),
    )


def serialize_briefing_for_response(
    record: DailyBriefingRecord,
    alerts: Iterable[BriefingAlertRecord] = (),
) -> dict[str, object]:
    return {
        "briefing_id": record.briefing_id,
        "briefing_date": record.briefing_date.isoformat(),
        "generated_at": record.generated_at.isoformat(),
        "lookback_started_at": record.lookback_started_at.isoformat(),
        "position_count": record.position_count,
        "base_currency": record.base_currency,
        "total_position_value": (
            str(record.total_position_value)
            if record.total_position_value is not None
            else None
        ),
        "cash_total": (
            str(record.cash_total) if record.cash_total is not None else None
        ),
        "fx_freshness_status": record.fx_freshness_status,
        "new_suggestion_count": record.new_suggestion_count,
        "new_decision_package_count": record.new_decision_package_count,
        "new_action_draft_count": record.new_action_draft_count,
        "diary_outcomes_closed_count": record.diary_outcomes_closed_count,
        "critical_event_count": record.critical_event_count,
        "alert_count": record.alert_count,
        "summary_nl": record.summary_nl,
        "help_nl": record.help_nl,
        "status": record.status,
        "blocking_reason": record.blocking_reason,
        "alerts": [
            {
                "alert_id": a.alert_id,
                "alert_kind": a.alert_kind,
                "severity": a.severity,
                "reference_kind": a.reference_kind,
                "reference_id": a.reference_id,
                "title_nl": a.title_nl,
                "body_nl": a.body_nl,
                "acknowledged_at": (
                    a.acknowledged_at.isoformat() if a.acknowledged_at else None
                ),
                "linked_at": a.linked_at.isoformat(),
            }
            for a in alerts
        ],
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


__all__ = [
    "DailyBriefingReport",
    "generate_daily_briefing",
    "serialize_briefing_for_response",
]
