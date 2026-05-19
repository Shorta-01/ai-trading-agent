from sqlalchemy import CheckConstraint

from ai_trading_agent_storage.metadata import metadata


def _check_constraints(table_name: str) -> dict[str, str]:
    table = metadata.tables[table_name]
    return {
        constraint.name: str(constraint.sqltext).lower()
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_paper_portfolio_setups_constraints_exist() -> None:
    check_constraints = _check_constraints("paper_portfolio_setups")
    assert set(check_constraints) == {
        "ck_paper_portfolio_setups_base_currency_eur",
        "ck_paper_portfolio_setups_starting_cash_amount_gt_0",
        "ck_paper_portfolio_setups_paper_only_true",
        "ck_paper_portfolio_setups_real_money_used_false",
        "ck_paper_portfolio_setups_broker_order_created_false",
        "ck_paper_portfolio_setups_live_trading_enabled_false",
        "ck_paper_portfolio_setups_user_confirmed_paper_only_true",
        "ck_paper_portfolio_setups_user_confirmed_no_real_money_true",
        "ck_paper_portfolio_setups_user_confirmed_no_broker_order_true",
    }


def test_paper_cash_accounts_constraints_exist() -> None:
    assert set(_check_constraints("paper_cash_accounts")) == {
        "ck_paper_cash_accounts_currency_eur",
        "ck_paper_cash_accounts_initial_paper_cash_amount_gt_0",
        "ck_paper_cash_accounts_paper_only_true",
    }


def test_audit_events_non_empty_constraints_exist() -> None:
    assert set(_check_constraints("audit_events")) == {
        "ck_audit_events_event_type_not_empty",
        "ck_audit_events_actor_type_not_empty",
        "ck_audit_events_entity_kind_not_empty",
        "ck_audit_events_summary_nl_not_empty",
    }


def test_broker_accounts_constraints_exist_and_include_required_checks() -> None:
    constraints = _check_constraints("broker_accounts")
    assert set(constraints) == {
        "ck_broker_accounts_broker_system_ibkr",
        "ck_broker_accounts_live_trading_allowed_false",
        "ck_broker_accounts_account_label_not_empty",
        "ck_broker_accounts_account_mode_not_empty",
        "ck_broker_accounts_connection_status_not_empty",
        "ck_broker_accounts_source_of_truth_status_not_empty",
        "ck_broker_accounts_explanation_nl_not_empty",
    }
    assert "ibkr" in constraints["ck_broker_accounts_broker_system_ibkr"]


def test_broker_sync_runs_constraints_exist_and_include_required_checks() -> None:
    constraints = _check_constraints("broker_sync_runs")
    assert set(constraints) == {
        "ck_broker_sync_runs_broker_system_ibkr",
        "ck_broker_sync_runs_sync_mode_not_empty",
        "ck_broker_sync_runs_sync_status_not_empty",
        "ck_broker_sync_runs_summary_nl_not_empty",
        "ck_broker_sync_runs_help_nl_not_empty",
        "ck_broker_sync_runs_completed_at_after_started_at",
    }
    assert "completed_at" in constraints["ck_broker_sync_runs_completed_at_after_started_at"]
    assert "started_at" in constraints["ck_broker_sync_runs_completed_at_after_started_at"]


def test_broker_position_snapshots_constraints_exist() -> None:
    constraints = _check_constraints("broker_position_snapshots")
    assert set(constraints) == {
        "ck_broker_position_snapshots_broker_system_ibkr",
        "ck_broker_position_snapshots_asset_identifier_not_empty",
        "ck_broker_position_snapshots_asset_symbol_not_empty",
        "ck_broker_position_snapshots_asset_type_not_empty",
        "ck_broker_position_snapshots_currency_not_empty",
        "ck_broker_position_snapshots_source_data_kind_not_empty",
        "ck_broker_position_snapshots_origin_not_empty",
        "ck_broker_position_snapshots_explanation_nl_not_empty",
    }


def test_broker_cash_snapshots_constraints_exist() -> None:
    constraints = _check_constraints("broker_cash_snapshots")
    assert set(constraints) == {
        "ck_broker_cash_snapshots_broker_system_ibkr",
        "ck_broker_cash_snapshots_currency_not_empty",
        "ck_broker_cash_snapshots_source_data_kind_not_empty",
        "ck_broker_cash_snapshots_origin_not_empty",
        "ck_broker_cash_snapshots_explanation_nl_not_empty",
    }
