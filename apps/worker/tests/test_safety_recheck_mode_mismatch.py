"""Task 134a — mode_mismatch gate isolation tests.

The brainstorm-locked two-tier check verifies that a draft created on
a ``DU*`` paper account doesn't get submitted while the gateway has
swapped to a live account (or vice versa). The gate function
implements Tier 1; Tier 2 (per-submit account-ID re-read) lives in
the submitter.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    BehaviouralGuardrailSettings,
    IbkrAccountCashSnapshotRecord,
)

from portfolio_outlook_worker.ibkr_submission.safety_recheck import (
    GatewaySnapshot,
    evaluate_submission_gates,
)

_NOW = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)


def _draft(account_id: str) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id="draft-1",
        decision_package_id=None,
        forecast_run_id=None,
        created_at=_NOW - timedelta(minutes=10),
        created_by="user",
        ibkr_account_id=account_id,
        conid="ASML.AS",
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        side="BUY",
        quantity=Decimal("6"),
        order_type="LMT",
        limit_price_local=Decimal("638.72"),
        time_in_force="DAY",
        notional_local=Decimal("3832.32"),
        notional_eur=Decimal("3832.32"),
        fx_rate_at_creation=Decimal("1"),
        usable_cash_eur_at_creation=Decimal("50000"),
        held_quantity_at_creation=None,
        status="user_approved",
        last_edited_at=None,
        user_approved_at=_NOW - timedelta(minutes=5),
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash="h-1",
        previous_draft_hash=None,
        safe_for_submission=False,
    )


def _cash() -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id="cash-1",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        base_currency="EUR",
        cash=Decimal("50000"),
        available_funds=Decimal("50000"),
        buying_power=Decimal("50000"),
        received_at=_NOW,
        stored_at=_NOW,
        ibkr_account_id="DU1234567",
    )


def _guardrails() -> BehaviouralGuardrailSettings:
    return BehaviouralGuardrailSettings.default_for_account(
        ibkr_account_id="DU1234567", last_updated_at=_NOW
    )


def test_paper_draft_against_live_gateway_blocks() -> None:
    """Draft approved on DU1234567 (paper); gateway is now live U7654321.

    The first gate that trips depends on order — mode_mismatch is
    evaluated before account_id_mismatch, so the locked reason here
    is ``mode_mismatch``.
    """

    result = evaluate_submission_gates(
        draft=_draft("DU1234567"),
        gateway=GatewaySnapshot(
            connected=True, account_id="U7654321", account_mode="live"
        ),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "mode_mismatch"
    assert "accountmodus" in result.explanation_nl


def test_live_draft_against_paper_gateway_blocks() -> None:
    """Draft approved on U7654321 (live); gateway is now paper DU1234567."""

    result = evaluate_submission_gates(
        draft=_draft("U7654321"),
        gateway=GatewaySnapshot(
            connected=True, account_id="DU1234567", account_mode="paper"
        ),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "mode_mismatch"


def test_paper_to_paper_account_id_mismatch_blocks() -> None:
    """Both sides paper, but account ID differs → account_id_mismatch."""

    result = evaluate_submission_gates(
        draft=_draft("DU1234567"),
        gateway=GatewaySnapshot(
            connected=True, account_id="DU9999999", account_mode="paper"
        ),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "account_id_mismatch"
