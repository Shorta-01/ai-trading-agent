from datetime import UTC, datetime

import pytest
from portfolio_outlook_domain import BackupPlan, BackupStatus, StorageReadinessStatus, build_not_ready_storage_check

from portfolio_outlook_portfolio import (
    InvalidAccountingInputError,
    check_storage_allows_paper_setup_persistence,
    check_storage_allows_transaction_persistence,
    require_storage_allows_paper_setup_persistence,
    require_storage_allows_transaction_persistence,
)


def test_not_ready_storage_rejected() -> None:
    check = build_not_ready_storage_check(checked_at=datetime.now(UTC))
    assert check_storage_allows_paper_setup_persistence(check) is False
    with pytest.raises(InvalidAccountingInputError):
        require_storage_allows_paper_setup_persistence(check)


def test_ready_storage_ok() -> None:
    check = build_not_ready_storage_check(checked_at=datetime.now(UTC))
    check.status = StorageReadinessStatus.READY_FOR_PERSISTENCE
    check.block_reasons = []
    check.can_persist_paper_setup = True
    check.can_persist_transactions = True
    check.can_persist_audit_events = True
    check.backup_plan = BackupPlan(backup_plan_id="bp1", status=BackupStatus.CONFIGURED, encrypted_required=True, restore_test_required=True, target_description_nl="x", explanation_nl="x")
    assert check_storage_allows_transaction_persistence(check) is True
    require_storage_allows_transaction_persistence(check)
