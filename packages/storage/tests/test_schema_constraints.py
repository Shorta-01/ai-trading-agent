from sqlalchemy import CheckConstraint

from ai_trading_agent_storage.metadata import metadata


def _check_names(table_name: str) -> set[str]:
    table = metadata.tables[table_name]
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_paper_portfolio_setups_constraints_exist() -> None:
    check_names = _check_names("paper_portfolio_setups")
    assert check_names == {
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
    assert _check_names("paper_cash_accounts") == {
        "ck_paper_cash_accounts_currency_eur",
        "ck_paper_cash_accounts_initial_paper_cash_amount_gt_0",
        "ck_paper_cash_accounts_paper_only_true",
    }


def test_audit_events_non_empty_constraints_exist() -> None:
    assert _check_names("audit_events") == {
        "ck_audit_events_event_type_not_empty",
        "ck_audit_events_actor_type_not_empty",
        "ck_audit_events_entity_kind_not_empty",
        "ck_audit_events_summary_nl_not_empty",
    }
