from sqlalchemy import DateTime, Numeric

from ai_trading_agent_storage.metadata import metadata


def test_metadata_imports_and_expected_tables_only() -> None:
    expected = {"paper_portfolio_setups", "paper_cash_accounts", "audit_events"}
    assert metadata is not None
    assert set(metadata.tables) == expected


def test_money_columns_are_numeric() -> None:
    assert isinstance(
        metadata.tables["paper_portfolio_setups"].c.starting_cash_amount.type,
        Numeric,
    )
    assert isinstance(
        metadata.tables["paper_cash_accounts"].c.initial_paper_cash_amount.type,
        Numeric,
    )


def test_timestamp_columns_are_timezone_aware() -> None:
    columns = [
        metadata.tables["paper_portfolio_setups"].c.created_at,
        metadata.tables["paper_portfolio_setups"].c.updated_at,
        metadata.tables["paper_cash_accounts"].c.created_at,
        metadata.tables["audit_events"].c.occurred_at,
        metadata.tables["audit_events"].c.created_at,
    ]
    for column in columns:
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True


def test_paper_cash_accounts_has_expected_setup_fk() -> None:
    setup_id_fk_targets = {
        fk.target_fullname
        for fk in metadata.tables["paper_cash_accounts"].c.setup_id.foreign_keys
    }
    assert setup_id_fk_targets == {"paper_portfolio_setups.setup_id"}


def test_required_paper_only_columns_exist() -> None:
    table = metadata.tables["paper_portfolio_setups"]
    for name in [
        "paper_only",
        "real_money_used",
        "broker_order_created",
        "live_trading_enabled",
        "user_confirmed_paper_only",
        "user_confirmed_no_real_money",
        "user_confirmed_no_broker_order",
    ]:
        assert name in table.c


def test_no_secret_like_column_names_and_no_legacy_table_names() -> None:
    forbidden_columns = {"password", "api_key", "secret_value", "access_token", "refresh_token"}
    forbidden_table_fragments = {"portfolio_outlook", "pom"}

    for table_name, table in metadata.tables.items():
        table_name_lower = table_name.lower()
        assert not any(fragment in table_name_lower for fragment in forbidden_table_fragments)

        for column_name in table.c.keys():
            column_name_lower = column_name.lower()
            assert not any(token in column_name_lower for token in forbidden_columns)
