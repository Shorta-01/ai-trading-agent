from datetime import UTC, datetime

import pytest
from portfolio_outlook_domain import (
    BrokerReconciliationDifference,
    BrokerReconciliationReport,
    BrokerSuggestionPolicy,
    BrokerSystem,
    ReconciliationDifferenceKind,
    ReconciliationSeverity,
    ReconciliationStatus,
    build_empty_reconciliation_report,
    build_ibkr_source_of_truth_policy,
)

from portfolio_outlook_portfolio import (
    check_reconciliation_allows_suggestions,
    require_reconciliation_allows_suggestions,
)
from portfolio_outlook_portfolio.errors import InvalidAccountingInputError


def _clean_report() -> BrokerReconciliationReport:
    return BrokerReconciliationReport(
        broker_reconciliation_report_id="r_clean",
        broker_sync_run_id="sync_1",
        broker_account_id="acct_1",
        broker_system=BrokerSystem.IBKR,
        status=ReconciliationStatus.CLEAN,
        differences=[],
        checked_at=datetime.now(UTC),
        source_of_truth_policy=build_ibkr_source_of_truth_policy(),
        suggestion_policy=BrokerSuggestionPolicy.ALLOW,
        can_create_suggestions=True,
        can_create_orders=False,
        title_nl="clean",
        summary_nl="clean",
        help_nl="clean",
    )


def test_reconciliation_guards():
    assert check_reconciliation_allows_suggestions(_clean_report())
    assert not check_reconciliation_allows_suggestions(
        build_empty_reconciliation_report(broker_sync_run_id="sync_1", checked_at=datetime.now(UTC))
    )

    diff = BrokerReconciliationDifference(
        broker_reconciliation_difference_id="d1",
        difference_kind=ReconciliationDifferenceKind.CASH_BALANCE_MISMATCH,
        severity=ReconciliationSeverity.BLOCKING,
        broker_account_id="acct_1",
        broker_system=BrokerSystem.IBKR,
        detected_at=datetime.now(UTC),
        broker_value="1",
        local_value="0",
        asset_identifier=None,
        currency="EUR",
        blocks_suggestions=True,
        requires_manual_review=False,
        summary_nl="verschil",
        help_nl="help",
        source_reference_ids=[],
        audit_event_ids=[],
    )
    report = _clean_report().model_copy(
        update={
            "status": ReconciliationStatus.DIFFERENCES_FOUND,
            "differences": [diff],
            "can_create_suggestions": False,
            "suggestion_policy": BrokerSuggestionPolicy.BLOCK_UNTIL_RECONCILED,
        }
    )
    assert not check_reconciliation_allows_suggestions(report)
    with pytest.raises(InvalidAccountingInputError):
        require_reconciliation_allows_suggestions(report)
