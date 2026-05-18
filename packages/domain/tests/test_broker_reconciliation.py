from datetime import datetime, UTC
from decimal import Decimal

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import *


def _difference(severity: ReconciliationSeverity = ReconciliationSeverity.BLOCKING) -> BrokerReconciliationDifference:
    return BrokerReconciliationDifference(
        broker_reconciliation_difference_id="diff_1",
        difference_kind=ReconciliationDifferenceKind.DIRECT_BROKER_EXECUTION,
        severity=severity,
        broker_account_id="acct_1",
        broker_system=BrokerSystem.IBKR,
        detected_at=datetime.now(UTC),
        broker_value="10",
        local_value="0",
        asset_identifier="NL000000",
        currency="EUR",
        blocks_suggestions=True,
        requires_manual_review=False,
        summary_nl="Verschil gevonden",
        help_nl="Controle nodig.",
        source_reference_ids=[],
        audit_event_ids=[],
    )


def test_policy_defaults():
    policy = build_ibkr_source_of_truth_policy()
    assert policy.ibkr_is_authoritative_for_broker_facts
    assert policy.local_system_is_authoritative_for_suggestions
    assert policy.local_system_is_authoritative_for_approvals
    assert policy.local_system_is_authoritative_for_explanations
    assert policy.no_silent_correction


def test_not_configured_builders_and_report():
    account = build_not_configured_broker_account_identity()
    plan = build_not_configured_broker_sync_plan()
    report = build_empty_reconciliation_report(broker_sync_run_id="sync_1", checked_at=datetime.now(UTC))
    assert not account.configured and not account.live_trading_allowed
    assert plan.requires_ibkr_configuration and not plan.planned_data_kinds
    assert report.status is ReconciliationStatus.NOT_AVAILABLE
    assert reconciliation_blocks_suggestions(report)


def test_snapshots_decimal_support():
    now = datetime.now(UTC)
    pos = BrokerPositionSnapshot(broker_position_snapshot_id="ps_1", broker_snapshot_id="s_1", broker_account_id="a_1", broker_system=BrokerSystem.IBKR, imported_at=now, asset_identifier="id", asset_symbol="SYM", asset_type="stock", currency="EUR", quantity=Decimal("1"), average_cost=Decimal("2"), market_value=Decimal("3"), source_data_kind=BrokerDataKind.POSITION, origin=BrokerActivityOrigin.IMPORTED_IBKR_POSITION, source_reference_ids=[], explanation_nl="ok")
    assert pos.quantity == Decimal("1")
    with pytest.raises(ValidationError):
        BrokerPositionSnapshot(**{**pos.model_dump(), "quantity": 1.1})


def test_execution_commission_and_blocking():
    now = datetime.now(UTC)
    exec_snapshot = BrokerExecutionSnapshot(broker_execution_snapshot_id="es_1", broker_snapshot_id="s_1", broker_account_id="a_1", broker_system=BrokerSystem.IBKR, imported_at=now, execution_time=now, execution_id="e1", order_id=None, asset_identifier="id", asset_symbol="SYM", asset_type="stock", side="buy", quantity=Decimal("1"), price=Decimal("10"), currency="EUR", origin=BrokerActivityOrigin.DIRECT_IBKR_ORDER, source_reference_ids=[], explanation_nl="ok")
    assert exec_snapshot.price == Decimal("10")
    comm = BrokerCommissionSnapshot(broker_commission_snapshot_id="cs_1", broker_snapshot_id="s_1", broker_account_id="a_1", broker_system=BrokerSystem.IBKR, imported_at=now, execution_id="e1", commission_amount=Decimal("1"), currency="EUR", realized_pnl=Decimal("2"), source_reference_ids=[], explanation_nl="ok")
    assert comm.realized_pnl == Decimal("2")


def test_report_rules_and_external_activity_and_secret_names():
    diff = _difference()
    report = BrokerReconciliationReport(
        broker_reconciliation_report_id="r_1",
        broker_sync_run_id="sync_1",
        broker_account_id="acct_1",
        broker_system=BrokerSystem.IBKR,
        status=ReconciliationStatus.DIFFERENCES_FOUND,
        differences=[diff],
        checked_at=datetime.now(UTC),
        source_of_truth_policy=build_ibkr_source_of_truth_policy(),
        suggestion_policy=BrokerSuggestionPolicy.BLOCK_UNTIL_RECONCILED,
        can_create_suggestions=False,
        can_create_orders=False,
        title_nl="t",
        summary_nl="s",
        help_nl="h",
    )
    assert reconciliation_blocks_suggestions(report)
    assert has_blocking_reconciliation_differences(report.differences)
    activity = classify_external_broker_activity_from_difference(diff, external_broker_activity_id="ext_1")
    assert activity.origin is BrokerActivityOrigin.DIRECT_IBKR_ORDER
    assert report.model_dump()

    model_classes = [BrokerSourceOfTruthPolicy, BrokerAccountIdentity, BrokerSyncPlan, BrokerPositionSnapshot, BrokerCashBalanceSnapshot, BrokerExecutionSnapshot, BrokerCommissionSnapshot, ExternalBrokerActivity, BrokerReconciliationDifference, BrokerReconciliationReport]
    forbidden = {"password", "token", "api_key", "secret"}
    for model in model_classes:
        assert forbidden.isdisjoint(model.model_fields)
