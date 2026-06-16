"""Action-draft orchestrator: turn ready Decision Packages into editable
LMT/DAY/whole-share drafts with Orderimpact + dry-run safety checks.

Hard contract — no order submission and no broker action lives in this
slice. Every persisted record has ``safe_for_submission`` /
``safe_for_orders`` / ``safe_for_broker_submission`` set to ``False``.
The dry-run result is persisted so the user can diagnose blockers and
edit later (editing arrives in a later slice).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetActionDraftRecord,
    AssetDecisionPackageRecord,
)
from portfolio_outlook_portfolio import (
    ACTIONABLE_LABELS,
    LOCKED_ORDER_TYPE,
    LOCKED_TIF,
    DraftSourceContext,
    compute_orderimpact,
    derive_action_draft_sizing,
    run_dry_run_safety_checks,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActionDraftSyncReport:
    requested_at: datetime
    completed_at: datetime
    draft_total: int
    draft_persisted: int
    draft_skipped_non_actionable: int
    draft_skipped_sizing_blocked: int
    draft_failed: int
    dry_run_passed: int
    dry_run_failed: int
    failures: tuple[dict[str, str], ...]
    status_nl: str
    help_nl: str


class _ActionDraftRepoProtocol(Protocol):
    def save_asset_action_draft(
        self, record: AssetActionDraftRecord
    ) -> object: ...


def _context_from_package(
    package: AssetDecisionPackageRecord,
    *,
    expected_account_mode: str,
    total_portfolio_value: Decimal | None,
    base_currency: str | None,
) -> DraftSourceContext:
    # FX is required when the package's asset currency differs from the
    # portfolio base currency. The package already denormalises the FX
    # snapshot details when applicable.
    fx_required = bool(
        base_currency
        and package.currency
        and package.currency.upper() != base_currency.upper()
    )
    return DraftSourceContext(
        decision_package_id=package.decision_package_id,
        decision_package_content_hash=package.content_hash,
        ibkr_conid=package.ibkr_conid,
        symbol=package.symbol,
        currency=package.currency,
        exchange=None,
        primary_exchange=None,
        # V1.2 §BZ (CLAUDE.md §15): account_mode tracks de operator-
        # verwachte account aan draft-tijd. De actuele IBKR-account
        # bepaalt het bestemmings-account bij submission; software
        # werkt VOLLEDIG in paper én live.
        account_mode=expected_account_mode,
        expected_account_mode=expected_account_mode,
        action_label=package.suggestion_action_label,
        action_label_nl=package.suggestion_action_label_nl,
        rationale_nl=package.rationale_nl,
        current_position_quantity=package.position_quantity or Decimal("0"),
        current_position_average_cost=package.position_average_cost,
        current_market_last_price=package.market_last_price,
        current_market_freshness_status=package.market_freshness_status,
        cash_amount=package.cash_amount,
        cash_currency=package.cash_base_currency,
        fx_required=fx_required,
        fx_freshness_status=package.fx_freshness_status,
        total_portfolio_value=total_portfolio_value,
        base_currency=base_currency,
    )


def generate_action_drafts(
    *,
    decision_packages: Iterable[AssetDecisionPackageRecord],
    repo: _ActionDraftRepoProtocol,
    expected_account_mode: str,
    total_portfolio_value: Decimal | None,
    base_currency: str | None,
    default_buy_value: Decimal,
    top_up_pct: Decimal,
    reduce_pct: Decimal,
    position_exchange_by_conid: dict[str, tuple[str | None, str | None]] | None = None,
) -> ActionDraftSyncReport:
    """Generate one draft per actionable Decision Package."""

    requested_at = datetime.now(UTC)
    draft_total = 0
    persisted = 0
    skipped_non_actionable = 0
    skipped_sizing_blocked = 0
    failed = 0
    dry_run_passed = 0
    dry_run_failed = 0
    failures: list[dict[str, str]] = []

    exchanges = position_exchange_by_conid or {}

    for package in decision_packages:
        draft_total += 1
        if package.suggestion_status != "ready":
            skipped_non_actionable += 1
            failures.append(
                {
                    "kind": "action_draft",
                    "decision_package_id": package.decision_package_id,
                    "reason": "decision_package_not_ready",
                }
            )
            continue
        if package.suggestion_action_label not in ACTIONABLE_LABELS:
            skipped_non_actionable += 1
            failures.append(
                {
                    "kind": "action_draft",
                    "decision_package_id": package.decision_package_id,
                    "reason": "non_actionable_label",
                    "label": package.suggestion_action_label,
                }
            )
            continue

        # Hydrate exchange from position snapshot when available
        exchange, primary_exchange = exchanges.get(package.ibkr_conid, (None, None))
        context = _context_from_package(
            package,
            expected_account_mode=expected_account_mode,
            total_portfolio_value=total_portfolio_value,
            base_currency=base_currency,
        )
        # Override exchange fields with what we know from the position
        # snapshot. ``DraftSourceContext`` is frozen so we rebuild it.
        context = DraftSourceContext(
            decision_package_id=context.decision_package_id,
            decision_package_content_hash=context.decision_package_content_hash,
            ibkr_conid=context.ibkr_conid,
            symbol=context.symbol,
            currency=context.currency,
            exchange=exchange,
            primary_exchange=primary_exchange,
            account_mode=context.account_mode,
            expected_account_mode=context.expected_account_mode,
            action_label=context.action_label,
            action_label_nl=context.action_label_nl,
            rationale_nl=context.rationale_nl,
            current_position_quantity=context.current_position_quantity,
            current_position_average_cost=context.current_position_average_cost,
            current_market_last_price=context.current_market_last_price,
            current_market_freshness_status=context.current_market_freshness_status,
            cash_amount=context.cash_amount,
            cash_currency=context.cash_currency,
            fx_required=context.fx_required,
            fx_freshness_status=context.fx_freshness_status,
            total_portfolio_value=context.total_portfolio_value,
            base_currency=context.base_currency,
        )

        sizing = derive_action_draft_sizing(
            context,
            default_buy_value_in_quote_currency=default_buy_value,
            top_up_pct=top_up_pct,
            reduce_pct=reduce_pct,
        )
        if sizing.status != "ready":
            skipped_sizing_blocked += 1
            failures.append(
                {
                    "kind": "action_draft",
                    "decision_package_id": package.decision_package_id,
                    "reason": sizing.blocking_reason or "sizing_blocked",
                }
            )
            continue

        impact = compute_orderimpact(context, sizing)
        dry_run = run_dry_run_safety_checks(context, sizing, impact)
        if dry_run.status == "passed":
            dry_run_passed += 1
            status = "dry_run_passed"
        else:
            dry_run_failed += 1
            status = "dry_run_failed"

        now = datetime.now(UTC)
        record = AssetActionDraftRecord(
            draft_id=f"draft_{uuid4().hex}",
            decision_package_id=package.decision_package_id,
            decision_package_content_hash=package.content_hash,
            ibkr_conid=package.ibkr_conid,
            symbol=package.symbol,
            currency=package.currency,
            exchange=exchange,
            primary_exchange=primary_exchange,
            # V1.2 §BZ (CLAUDE.md §15): account_mode tracks de operator-
        # verwachte account aan draft-tijd. De actuele IBKR-account
        # bepaalt het bestemmings-account bij submission; software
        # werkt VOLLEDIG in paper én live.
        account_mode=expected_account_mode,
            expected_account_mode=expected_account_mode,
            action_side=sizing.action_side,
            order_type=LOCKED_ORDER_TYPE,
            tif=LOCKED_TIF,
            quantity=sizing.quantity,
            limit_price=sizing.limit_price,
            estimated_order_value=impact.estimated_order_value,
            estimated_cash_before=impact.estimated_cash_before,
            estimated_cash_after=impact.estimated_cash_after,
            estimated_position_quantity_before=impact.estimated_position_quantity_before,
            estimated_position_quantity_after=impact.estimated_position_quantity_after,
            estimated_position_value_after=impact.estimated_position_value_after,
            estimated_portfolio_weight_after_pct=impact.estimated_portfolio_weight_after_pct,
            estimated_concentration_impact_pct=impact.estimated_concentration_impact_pct,
            orderimpact_base_currency=impact.base_currency,
            estimated_belgian_tob=impact.estimated_belgian_tob,
            belgian_tob_security_class=impact.belgian_tob_security_class,
            source_action_label=package.suggestion_action_label,
            source_action_label_nl=package.suggestion_action_label_nl,
            status=status,
            dry_run_status=dry_run.status,
            dry_run_failures_json=dry_run.failures if dry_run.failures else None,
            blocking_reason=None,
            rationale_nl=package.rationale_nl,
            explanation_nl=(
                f"Bewerkbare {sizing.action_side}-draft op basis van Decision "
                f"Package {package.decision_package_id} ({package.symbol}); "
                "LMT/DAY/hele aandelen. Geen ordersubmissie."
            ),
            created_at=now,
            updated_at=now,
        )
        try:
            repo.save_asset_action_draft(record)
        except Exception as exc:
            failed += 1
            failures.append(
                {
                    "kind": "action_draft",
                    "decision_package_id": package.decision_package_id,
                    "reason": "persistence_error",
                    "detail": str(exc),
                }
            )
            continue
        persisted += 1

    completed_at = datetime.now(UTC)
    if draft_total == 0:
        status_nl = "Geen Decision Packages beschikbaar"
        help_nl = "Voer eerst decision-packages-sync uit."
    elif persisted == 0:
        status_nl = "Geen action drafts opgeslagen"
        help_nl = "Geen actionable Decision Packages of sizing geblokkeerd; zie failures."
    elif failed or skipped_sizing_blocked or skipped_non_actionable:
        status_nl = "Action drafts gedeeltelijk voltooid"
        help_nl = "Sommige Decision Packages produceerden geen draft; zie failures."
    else:
        status_nl = "Action drafts voltooid"
        help_nl = "Alle actionable Decision Packages hebben een draft + dry-run."

    return ActionDraftSyncReport(
        requested_at=requested_at,
        completed_at=completed_at,
        draft_total=draft_total,
        draft_persisted=persisted,
        draft_skipped_non_actionable=skipped_non_actionable,
        draft_skipped_sizing_blocked=skipped_sizing_blocked,
        draft_failed=failed,
        dry_run_passed=dry_run_passed,
        dry_run_failed=dry_run_failed,
        failures=tuple(failures),
        status_nl=status_nl,
        help_nl=help_nl,
    )


def _decimal_or_none_str(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def serialize_action_draft_for_response(
    record: AssetActionDraftRecord,
) -> dict[str, object]:
    return {
        "draft_id": record.draft_id,
        "decision_package_id": record.decision_package_id,
        "decision_package_content_hash": record.decision_package_content_hash,
        "ibkr_conid": record.ibkr_conid,
        "symbol": record.symbol,
        "currency": record.currency,
        "exchange": record.exchange,
        "primary_exchange": record.primary_exchange,
        "account_mode": record.account_mode,
        "expected_account_mode": record.expected_account_mode,
        "action_side": record.action_side,
        "order_type": record.order_type,
        "tif": record.tif,
        "quantity": str(record.quantity),
        "limit_price": str(record.limit_price),
        "estimated_order_value": _decimal_or_none_str(record.estimated_order_value),
        "estimated_cash_before": _decimal_or_none_str(record.estimated_cash_before),
        "estimated_cash_after": _decimal_or_none_str(record.estimated_cash_after),
        "estimated_position_quantity_before": _decimal_or_none_str(
            record.estimated_position_quantity_before
        ),
        "estimated_position_quantity_after": _decimal_or_none_str(
            record.estimated_position_quantity_after
        ),
        "estimated_position_value_after": _decimal_or_none_str(
            record.estimated_position_value_after
        ),
        "estimated_portfolio_weight_after_pct": _decimal_or_none_str(
            record.estimated_portfolio_weight_after_pct
        ),
        "estimated_concentration_impact_pct": _decimal_or_none_str(
            record.estimated_concentration_impact_pct
        ),
        "orderimpact_base_currency": record.orderimpact_base_currency,
        "estimated_belgian_tob": _decimal_or_none_str(record.estimated_belgian_tob),
        "belgian_tob_security_class": record.belgian_tob_security_class,
        "source_action_label": record.source_action_label,
        "source_action_label_nl": record.source_action_label_nl,
        "status": record.status,
        "dry_run_status": record.dry_run_status,
        "dry_run_failures": list(record.dry_run_failures_json or ()),
        "blocking_reason": record.blocking_reason,
        "rationale_nl": record.rationale_nl,
        "explanation_nl": record.explanation_nl,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "safe_for_submission": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
    }
