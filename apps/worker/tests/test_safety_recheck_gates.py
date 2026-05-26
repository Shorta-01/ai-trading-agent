"""Task 134a — table-driven coverage of every submission gate.

Each test exercises exactly one gate by tripping it while keeping
every other input on the happy path. The locked Dutch explanations
are surfaced as ``explanation_nl`` and asserted against the
``_DUTCH_EXPLANATIONS`` map indirectly via substring matches.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    BehaviouralGuardrailSettings,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
)

from portfolio_outlook_worker.ibkr_submission.safety_recheck import (
    DrawdownContext,
    FomoContext,
    GatewaySnapshot,
    MarketHoursProviderProtocol,
    RecentSubmissionRecord,
    evaluate_submission_gates,
)

_NOW = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)


def _draft(
    *,
    side: str = "BUY",
    status: str = "user_approved",
    account_id: str = "DU1234567",
    notional_eur: Decimal = Decimal("3832.32"),
    quantity: Decimal = Decimal("6"),
    limit_price: Decimal = Decimal("638.72"),
    exchange: str = "AEB",
) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id="draft-1",
        decision_package_id=None,
        forecast_run_id=None,
        created_at=_NOW - timedelta(minutes=10),
        created_by="user",
        ibkr_account_id=account_id,
        conid="ASML.AS",
        symbol="ASML",
        exchange=exchange,
        currency_local="EUR",
        side=side,
        quantity=quantity,
        order_type="LMT",
        limit_price_local=limit_price,
        time_in_force="DAY",
        notional_local=notional_eur,
        notional_eur=notional_eur,
        fx_rate_at_creation=Decimal("1"),
        usable_cash_eur_at_creation=Decimal("50000"),
        held_quantity_at_creation=None,
        status=status,
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


def _cash(amount: Decimal = Decimal("50000")) -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id="cash-1",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        base_currency="EUR",
        cash=amount,
        available_funds=amount,
        buying_power=amount,
        received_at=_NOW,
        stored_at=_NOW,
        ibkr_account_id="DU1234567",
    )


def _position(qty: Decimal = Decimal("100")) -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id="pos-1",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        security_type="STK",
        currency="EUR",
        exchange="AEB",
        primary_exchange="AEB",
        quantity=qty,
        average_cost=Decimal("500"),
        received_at=_NOW,
        stored_at=_NOW,
        ibkr_account_id="DU1234567",
    )


def _gateway_ok() -> GatewaySnapshot:
    return GatewaySnapshot(
        connected=True, account_id="DU1234567", account_mode="paper"
    )


def _guardrails() -> BehaviouralGuardrailSettings:
    return BehaviouralGuardrailSettings.default_for_account(
        ibkr_account_id="DU1234567", last_updated_at=_NOW
    )


class _AlwaysOpenMarket(MarketHoursProviderProtocol):
    def is_open(self, *, exchange: str, now: datetime) -> bool:
        return True


class _AlwaysClosedMarket(MarketHoursProviderProtocol):
    def is_open(self, *, exchange: str, now: datetime) -> bool:
        return False


def test_happy_path_returns_ok() -> None:
    result = evaluate_submission_gates(
        draft=_draft(),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        in_flight_drafts_for_conid=(),
        drawdown=None,
        fomo=None,
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert result.ok is True
    assert result.block_reason is None


def test_connection_down_blocks() -> None:
    gateway = GatewaySnapshot(
        connected=False, account_id="DU1234567", account_mode="paper"
    )
    result = evaluate_submission_gates(
        draft=_draft(),
        gateway=gateway,
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "connection_down"
    assert "IBKR-verbinding" in result.explanation_nl


def test_account_id_mismatch_blocks() -> None:
    gateway = GatewaySnapshot(
        connected=True, account_id="U7654321", account_mode="live"
    )
    result = evaluate_submission_gates(
        draft=_draft(account_id="U7654321"),
        gateway=gateway,
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        now=_NOW,
    )
    # The draft is for a live account but the gateway also reports
    # live + matching account ID; this should pass.
    assert result.ok is True
    # Now flip the gateway's reported account id to mismatch.
    bad_gateway = GatewaySnapshot(
        connected=True, account_id="U9999999", account_mode="live"
    )
    result_bad = evaluate_submission_gates(
        draft=_draft(account_id="U7654321"),
        gateway=bad_gateway,
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        now=_NOW,
    )
    assert result_bad.ok is False
    assert result_bad.block_reason == "account_id_mismatch"


def test_market_closed_blocks() -> None:
    result = evaluate_submission_gates(
        draft=_draft(),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        market_hours=_AlwaysClosedMarket(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "market_closed"


def test_duplicate_in_flight_blocks() -> None:
    existing = _draft()
    in_flight = ActionDraftEntry(  # different ID, same (account, conid)
        **{
            **existing.__dict__,
            "action_draft_id": "draft-other",
            "status": "submitted",
        }
    )
    result = evaluate_submission_gates(
        draft=_draft(),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        in_flight_drafts_for_conid=(in_flight,),
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "duplicate_in_flight"


def test_hard_drawdown_blocks_buy_and_sell() -> None:
    drawdown = DrawdownContext(
        soft_loss_pct=Decimal("-2"), hard_loss_pct=Decimal("-11")
    )
    for side in ("BUY", "SELL"):
        result = evaluate_submission_gates(
            draft=_draft(side=side),
            gateway=_gateway_ok(),
            cash_snapshot=_cash(),
            position_snapshot=_position() if side == "SELL" else None,
            guardrail_settings=_guardrails(),
            recent_submissions=(),
            drawdown=drawdown,
            market_hours=_AlwaysOpenMarket(),
            now=_NOW,
        )
        assert result.ok is False
        assert result.block_reason == "hard_drawdown", (
            f"side={side}: {result}"
        )


def test_soft_drawdown_blocks_buy_only() -> None:
    drawdown = DrawdownContext(
        soft_loss_pct=Decimal("-6"), hard_loss_pct=Decimal("-2")
    )
    buy_result = evaluate_submission_gates(
        draft=_draft(side="BUY"),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        drawdown=drawdown,
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert buy_result.ok is False
    assert buy_result.block_reason == "soft_drawdown"

    sell_result = evaluate_submission_gates(
        draft=_draft(side="SELL"),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=_position(),
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        drawdown=drawdown,
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert sell_result.ok is True


def test_daily_limit_blocks_at_threshold() -> None:
    recent = tuple(
        RecentSubmissionRecord(
            submitted_at=_NOW - timedelta(hours=h),
            result="placed",
            sent_to_account_id="DU1234567",
        )
        for h in range(5)
    )
    result = evaluate_submission_gates(
        draft=_draft(),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=recent,
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "daily_limit"


def test_cooldown_blocks_within_window() -> None:
    recent = (
        RecentSubmissionRecord(
            submitted_at=_NOW - timedelta(seconds=30),
            result="placed",
            sent_to_account_id="DU1234567",
        ),
    )
    result = evaluate_submission_gates(
        draft=_draft(),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=recent,
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "cooldown"


def test_cash_insufficient_blocks_buy() -> None:
    result = evaluate_submission_gates(
        draft=_draft(),  # needs 3832 EUR
        gateway=_gateway_ok(),
        cash_snapshot=_cash(Decimal("100")),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "cash_insufficient"


def test_position_insufficient_blocks_sell() -> None:
    result = evaluate_submission_gates(
        draft=_draft(side="SELL", quantity=Decimal("200")),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=_position(Decimal("10")),
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "cash_insufficient"


def test_fomo_drift_blocks_above_threshold() -> None:
    # Approved at 638.72, drifted to 660 → ~3.3% above threshold of 1.5%.
    fomo = FomoContext(current_price_local=Decimal("660"))
    result = evaluate_submission_gates(
        draft=_draft(),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        fomo=fomo,
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "fomo"


def test_fomo_within_threshold_ok() -> None:
    # 638.72 → 640 is ~0.2% drift; below threshold.
    fomo = FomoContext(current_price_local=Decimal("640"))
    result = evaluate_submission_gates(
        draft=_draft(),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        fomo=fomo,
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert result.ok is True


def test_non_user_approved_status_blocks() -> None:
    result = evaluate_submission_gates(
        draft=_draft(status="proposed"),
        gateway=_gateway_ok(),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        market_hours=_AlwaysOpenMarket(),
        now=_NOW,
    )
    assert result.ok is False
    assert result.block_reason == "unknown"


def test_block_reason_uses_locked_dutch_explanations() -> None:
    result = evaluate_submission_gates(
        draft=_draft(),
        gateway=GatewaySnapshot(
            connected=False, account_id="DU1234567", account_mode="paper"
        ),
        cash_snapshot=_cash(),
        position_snapshot=None,
        guardrail_settings=_guardrails(),
        recent_submissions=(),
        now=_NOW,
    )
    # The Dutch message is a locked sentence; assert a stable substring.
    assert "IBKR" in result.explanation_nl
    assert result.failed_gates == ("gateway_connected",)
