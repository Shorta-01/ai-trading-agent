"""Tests for the approve + submit-to-paper orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trading_agent_storage import (
    AssetActionDraftEventRecord,
    AssetActionDraftRecord,
    AssetActionDraftSubmissionRecord,
)

from portfolio_outlook_api.action_draft_submission import (
    approve_action_draft,
    submit_action_draft_to_paper,
)
from portfolio_outlook_api.ibkr_ibapi_order_submission_client import (
    OrderSubmissionInputs,
    OrderSubmissionResult,
)

_NOW = datetime(2025, 5, 24, 10, 0, tzinfo=UTC)


def _draft(
    *,
    dry_run_status: str = "passed",
    dry_run_failures: tuple[str, ...] | None = None,
    account_mode: str = "paper",
    quantity: str = "5",
    limit_price: str = "180",
    action_side: str = "BUY",
) -> AssetActionDraftRecord:
    return AssetActionDraftRecord(
        draft_id="draft-1",
        decision_package_id="dp-1",
        decision_package_content_hash="hash-1",
        ibkr_conid="265598",
        symbol="AAPL",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        account_mode=account_mode,
        expected_account_mode="paper",
        action_side=action_side,
        order_type="LMT",
        tif="DAY",
        quantity=Decimal(quantity),
        limit_price=Decimal(limit_price),
        estimated_order_value=Decimal("900"),
        estimated_cash_before=Decimal("10000"),
        estimated_cash_after=Decimal("9100"),
        estimated_position_quantity_before=Decimal("0"),
        estimated_position_quantity_after=Decimal("5"),
        estimated_position_value_after=Decimal("900"),
        estimated_portfolio_weight_after_pct=Decimal("9.0"),
        estimated_concentration_impact_pct=Decimal("9.0"),
        orderimpact_base_currency="USD",
        source_action_label="Kopen",
        source_action_label_nl="Kopen",
        status="dry_run_passed",
        dry_run_status=dry_run_status,
        dry_run_failures_json=dry_run_failures,
        blocking_reason=None,
        rationale_nl="rationale",
        explanation_nl="explanation",
        created_at=_NOW,
        updated_at=_NOW,
    )


class FakeSubmissionRepo:
    def __init__(self, existing: AssetActionDraftSubmissionRecord | None = None) -> None:
        self._existing = existing
        self.saved: list[AssetActionDraftSubmissionRecord] = []

    def upsert_asset_action_draft_submission(
        self, record: AssetActionDraftSubmissionRecord
    ) -> object:
        self.saved.append(record)
        self._existing = record
        return None

    def get_submission_by_draft_id(self, draft_id: str) -> object:
        return type(
            "_Read",
            (),
            {
                "found": self._existing is not None,
                "record": self._existing,
            },
        )()


class FakeEventRepo:
    def __init__(self) -> None:
        self.saved: list[AssetActionDraftEventRecord] = []

    def save_asset_action_draft_event(
        self, record: AssetActionDraftEventRecord
    ) -> object:
        self.saved.append(record)
        return None


class FakeSubmissionClient:
    def __init__(
        self,
        *,
        result: OrderSubmissionResult,
        captured_inputs: list[OrderSubmissionInputs] | None = None,
    ) -> None:
        self.result = result
        self.captured_inputs = captured_inputs if captured_inputs is not None else []
        self.closed = False

    def submit(self, inputs: OrderSubmissionInputs) -> OrderSubmissionResult:
        self.captured_inputs.append(inputs)
        return self.result

    def close(self) -> None:
        self.closed = True


# ---- approve_action_draft -------------------------------------------------


def test_approve_blocks_when_dry_run_not_passed() -> None:
    submission_repo = FakeSubmissionRepo()
    event_repo = FakeEventRepo()

    result = approve_action_draft(
        draft=_draft(dry_run_status="failed", dry_run_failures=("market_data_not_fresh",)),
        submission_repo=submission_repo,
        event_repo=event_repo,
        expected_account_mode="paper",
        provider_code="ibkr",
    )

    assert result.status == "blocked"
    assert result.blocking_reason == "dry_run_not_passed"
    assert submission_repo.saved == []
    # An event is logged for the blocked approval attempt
    assert any(e.event_type == "approval_blocked" for e in event_repo.saved)


def test_approve_blocks_when_account_mode_is_not_paper() -> None:
    submission_repo = FakeSubmissionRepo()
    event_repo = FakeEventRepo()

    result = approve_action_draft(
        draft=_draft(account_mode="live"),
        submission_repo=submission_repo,
        event_repo=event_repo,
        expected_account_mode="paper",
        provider_code="ibkr",
    )

    assert result.status == "blocked"
    assert result.blocking_reason == "paper_only_required"


def test_approve_blocks_when_expected_account_mode_is_not_paper() -> None:
    submission_repo = FakeSubmissionRepo()
    event_repo = FakeEventRepo()

    result = approve_action_draft(
        draft=_draft(),
        submission_repo=submission_repo,
        event_repo=event_repo,
        expected_account_mode="live",
        provider_code="ibkr",
    )

    assert result.status == "blocked"
    assert result.blocking_reason == "expected_account_mode_not_paper"


def test_approve_persists_user_approved_submission_with_safety_flags_false() -> None:
    submission_repo = FakeSubmissionRepo()
    event_repo = FakeEventRepo()

    result = approve_action_draft(
        draft=_draft(),
        submission_repo=submission_repo,
        event_repo=event_repo,
        expected_account_mode="paper",
        provider_code="ibkr",
    )

    assert result.status == "approved"
    assert result.state == "user_approved"
    record = submission_repo.saved[0]
    assert record.approval_status == "approved"
    assert record.state == "user_approved"
    assert record.safe_for_broker_submission is False
    assert record.safe_for_orders is False
    # Critical event written
    assert any(
        e.event_type == "approved" and e.severity == "critical"
        for e in event_repo.saved
    )


# ---- submit_action_draft_to_paper ----------------------------------------


def _existing_approved_submission(
    *, approved_minutes_ago: int = 1
) -> AssetActionDraftSubmissionRecord:
    approved_at = datetime.now(UTC) - timedelta(minutes=approved_minutes_ago)
    return AssetActionDraftSubmissionRecord(
        submission_id="sub-1",
        draft_id="draft-1",
        state="user_approved",
        approval_status="approved",
        approved_at=approved_at,
        approved_by="owner",
        approval_dry_run_status="passed",
        approval_dry_run_failures_json=None,
        submitted_at=None,
        ibkr_order_id=None,
        ibkr_perm_id=None,
        ibkr_client_id=None,
        ibkr_status_text=None,
        filled_quantity=None,
        remaining_quantity=None,
        average_fill_price=None,
        cancelled_at=None,
        cancellation_reason=None,
        rejected_reason=None,
        reconciled_at=None,
        account_mode="paper",
        expected_account_mode="paper",
        provider_code="ibkr",
        created_at=approved_at,
        updated_at=approved_at,
        last_state_transition_at=approved_at,
    )


def test_submit_blocks_when_submission_client_is_none() -> None:
    submission_repo = FakeSubmissionRepo(existing=_existing_approved_submission())
    event_repo = FakeEventRepo()

    result = submit_action_draft_to_paper(
        draft=_draft(),
        submission_repo=submission_repo,
        event_repo=event_repo,
        submission_client=None,
        expected_account_mode="paper",
        provider_code="ibkr",
        approval_valid_minutes=5,
    )

    assert result.status == "blocked"
    assert result.blocking_reason == "submission_client_unavailable"


def test_submit_blocks_when_draft_is_not_paper_account_mode() -> None:
    submission_repo = FakeSubmissionRepo(existing=_existing_approved_submission())
    event_repo = FakeEventRepo()
    client = FakeSubmissionClient(
        result=OrderSubmissionResult(True, 100, 500, 11, "Submitted", None)
    )

    result = submit_action_draft_to_paper(
        draft=_draft(account_mode="live"),
        submission_repo=submission_repo,
        event_repo=event_repo,
        submission_client=client,  # type: ignore[arg-type]
        expected_account_mode="paper",
        provider_code="ibkr",
        approval_valid_minutes=5,
    )

    assert result.status == "blocked"
    assert result.blocking_reason == "paper_only_required"


def test_submit_blocks_when_approval_is_missing() -> None:
    submission_repo = FakeSubmissionRepo(existing=None)  # no approval yet
    event_repo = FakeEventRepo()
    client = FakeSubmissionClient(
        result=OrderSubmissionResult(True, 100, 500, 11, "Submitted", None)
    )

    result = submit_action_draft_to_paper(
        draft=_draft(),
        submission_repo=submission_repo,
        event_repo=event_repo,
        submission_client=client,  # type: ignore[arg-type]
        expected_account_mode="paper",
        provider_code="ibkr",
        approval_valid_minutes=5,
    )

    assert result.status == "blocked"
    assert result.blocking_reason == "approval_missing"


def test_submit_blocks_when_approval_expired() -> None:
    submission_repo = FakeSubmissionRepo(
        existing=_existing_approved_submission(approved_minutes_ago=120)
    )
    event_repo = FakeEventRepo()
    client = FakeSubmissionClient(
        result=OrderSubmissionResult(True, 100, 500, 11, "Submitted", None)
    )

    result = submit_action_draft_to_paper(
        draft=_draft(),
        submission_repo=submission_repo,
        event_repo=event_repo,
        submission_client=client,  # type: ignore[arg-type]
        expected_account_mode="paper",
        provider_code="ibkr",
        approval_valid_minutes=5,
    )

    assert result.status == "blocked"
    assert result.blocking_reason == "approval_expired"


def test_submit_happy_path_calls_real_client_and_persists_submitted_state() -> None:
    submission_repo = FakeSubmissionRepo(existing=_existing_approved_submission())
    event_repo = FakeEventRepo()
    client = FakeSubmissionClient(
        result=OrderSubmissionResult(
            accepted=True,
            ibkr_order_id=100,
            ibkr_perm_id=999,
            ibkr_client_id=11,
            ibkr_status_text="Submitted",
            rejected_reason=None,
        )
    )

    result = submit_action_draft_to_paper(
        draft=_draft(),
        submission_repo=submission_repo,
        event_repo=event_repo,
        submission_client=client,  # type: ignore[arg-type]
        expected_account_mode="paper",
        provider_code="ibkr",
        approval_valid_minutes=5,
    )

    assert result.status == "submitted"
    assert result.state == "awaiting_ibkr_reply"
    assert result.ibkr_order_id == 100
    assert result.ibkr_perm_id == 999
    assert client.closed is True
    # The fake client was given the right inputs (action / quantity / price).
    inputs = client.captured_inputs[0]
    assert inputs.action_side == "BUY"
    assert inputs.quantity == Decimal("5")
    assert inputs.limit_price == Decimal("180")
    assert inputs.primary_exchange == "NASDAQ"
    # State persisted
    persisted = submission_repo.saved[-1]
    assert persisted.state == "awaiting_ibkr_reply"
    assert persisted.ibkr_order_id == 100
    assert persisted.ibkr_perm_id == 999
    assert persisted.safe_for_broker_submission is False
    assert persisted.safe_for_orders is False
    # Critical event
    assert any(
        e.event_type == "submitted" and e.severity == "critical" for e in event_repo.saved
    )


def test_submit_handles_ibkr_rejection_and_persists_rejected_state() -> None:
    submission_repo = FakeSubmissionRepo(existing=_existing_approved_submission())
    event_repo = FakeEventRepo()
    client = FakeSubmissionClient(
        result=OrderSubmissionResult(
            accepted=False,
            ibkr_order_id=100,
            ibkr_perm_id=None,
            ibkr_client_id=11,
            ibkr_status_text="Cancelled",
            rejected_reason="201:Order rejected",
        )
    )

    result = submit_action_draft_to_paper(
        draft=_draft(),
        submission_repo=submission_repo,
        event_repo=event_repo,
        submission_client=client,  # type: ignore[arg-type]
        expected_account_mode="paper",
        provider_code="ibkr",
        approval_valid_minutes=5,
    )

    assert result.status == "rejected"
    assert result.state == "rejected"
    assert client.closed is True
    persisted = submission_repo.saved[-1]
    assert persisted.state == "rejected"
    assert persisted.rejected_reason == "201:Order rejected"
    assert any(
        e.event_type == "submission_failed" and e.severity == "critical"
        for e in event_repo.saved
    )


@pytest.mark.parametrize("dry_run_status", ["failed", "not_attempted"])
def test_submit_blocks_when_dry_run_was_not_passed(dry_run_status: str) -> None:
    submission_repo = FakeSubmissionRepo(existing=_existing_approved_submission())
    event_repo = FakeEventRepo()
    client = FakeSubmissionClient(
        result=OrderSubmissionResult(True, 100, 500, 11, "Submitted", None)
    )

    result = submit_action_draft_to_paper(
        draft=_draft(dry_run_status=dry_run_status),
        submission_repo=submission_repo,
        event_repo=event_repo,
        submission_client=client,  # type: ignore[arg-type]
        expected_account_mode="paper",
        provider_code="ibkr",
        approval_valid_minutes=5,
    )

    assert result.status == "blocked"
    assert result.blocking_reason == "dry_run_not_passed"
    # The real client must NOT have been invoked.
    assert client.captured_inputs == []
