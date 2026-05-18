from portfolio_outlook_domain import (
    BrokerReconciliationDifference,
    BrokerReconciliationReport,
    ReconciliationStatus,
    has_blocking_reconciliation_differences,
    reconciliation_blocks_suggestions,
)

from .errors import InvalidAccountingInputError


def check_reconciliation_allows_suggestions(report: BrokerReconciliationReport) -> bool:
    if reconciliation_blocks_suggestions(report):
        return False
    return report.status is ReconciliationStatus.CLEAN and report.can_create_suggestions


def require_reconciliation_allows_suggestions(report: BrokerReconciliationReport) -> None:
    if not check_reconciliation_allows_suggestions(report):
        raise InvalidAccountingInputError(
            "Actiesuggesties zijn geblokkeerd door brokerreconciliatie."
        )


def check_no_blocking_reconciliation_differences(
    differences: list[BrokerReconciliationDifference],
) -> bool:
    return not has_blocking_reconciliation_differences(differences)
