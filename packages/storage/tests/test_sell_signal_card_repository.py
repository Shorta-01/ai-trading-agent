"""Tests voor ``SqlAlchemySellSignalCardRepository`` (V1.2 §BF)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from ai_trading_agent_storage import (
    SELL_SIGNAL_ACTION_HOLD,
    SELL_SIGNAL_ACTION_SUGGEST_SELL,
    SELL_SIGNAL_KIND_HOLD_REVIEW,
    SELL_SIGNAL_KIND_TAKE_PROFIT,
    SaveSellSignalCardRequest,
    SellSignalCardRecord,
    SqlAlchemySellSignalCardRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)


@pytest.fixture
def connection():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(32) NOT NULL)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('0079_macro_index_snapshots')"
            )
        )
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
    finally:
        trans.rollback()
        conn.close()
        engine.dispose()


def _readiness() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0079_macro_index_snapshots",
        database_revision_id="0079_macro_index_snapshots",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="ok",
    )


_EVAL_AT = datetime(2026, 6, 14, 10, 30, tzinfo=UTC)


def _take_profit_request(
    *,
    symbol: str = "AAPL",
    action: str = SELL_SIGNAL_ACTION_SUGGEST_SELL,
    current_price: str = "104.50",
    reset_dismissal: bool = False,
    evaluated_at: datetime = _EVAL_AT,
) -> SaveSellSignalCardRequest:
    return SaveSellSignalCardRequest(
        card_id=f"sscv_{uuid4().hex}",
        ibkr_account_ref="paper",
        symbol=symbol,
        currency="USD",
        signal_kind=SELL_SIGNAL_KIND_TAKE_PROFIT,
        action=action,
        entry_price=Decimal("100"),
        current_price=Decimal(current_price),
        quantity=100,
        current_pct_return=Decimal("4.50"),
        target_pct=Decimal("4"),
        target_reached=True,
        days_held=None,
        forecast_id="fc_x",
        forecaster_above_target=None,
        position_in_loss=None,
        short_term_p50=Decimal("110"),
        short_term_horizon_days=90,
        short_term_prob_above_pct=Decimal("60"),
        expected_net_proceeds_eur=None,
        headline_nl="VERKOOP — AAPL staat op +4,5%, neem je winst",
        detail_nl="Korte termijn forecast p50 €110",
        evaluated_at=evaluated_at,
        reset_dismissal=reset_dismissal,
    )


# ----------------------------------------------------------------------
# Record validation
# ----------------------------------------------------------------------


def test_record_rejects_unknown_signal_kind() -> None:
    with pytest.raises(ValueError, match="signal_kind"):
        SellSignalCardRecord(
            card_id="c",
            ibkr_account_ref="paper",
            symbol="AAPL",
            currency="USD",
            signal_kind="foo",  # invalid
            action=SELL_SIGNAL_ACTION_HOLD,
            entry_price=Decimal("100"),
            current_price=Decimal("100"),
            quantity=10,
            current_pct_return=Decimal("0"),
            target_pct=None,
            target_reached=None,
            days_held=None,
            forecast_id=None,
            forecaster_above_target=None,
            position_in_loss=None,
            short_term_p50=None,
            short_term_horizon_days=None,
            short_term_prob_above_pct=None,
            expected_net_proceeds_eur=None,
            headline_nl="x",
            detail_nl="x",
            first_generated_at=_EVAL_AT,
            last_evaluated_at=_EVAL_AT,
            dismissed_at=None,
            dismissed_reason=None,
        )


def test_record_rejects_unknown_action() -> None:
    with pytest.raises(ValueError, match="action"):
        SellSignalCardRecord(
            card_id="c",
            ibkr_account_ref="paper",
            symbol="AAPL",
            currency="USD",
            signal_kind=SELL_SIGNAL_KIND_TAKE_PROFIT,
            action="foo",
            entry_price=Decimal("100"),
            current_price=Decimal("100"),
            quantity=10,
            current_pct_return=Decimal("0"),
            target_pct=None,
            target_reached=None,
            days_held=None,
            forecast_id=None,
            forecaster_above_target=None,
            position_in_loss=None,
            short_term_p50=None,
            short_term_horizon_days=None,
            short_term_prob_above_pct=None,
            expected_net_proceeds_eur=None,
            headline_nl="x",
            detail_nl="x",
            first_generated_at=_EVAL_AT,
            last_evaluated_at=_EVAL_AT,
            dismissed_at=None,
            dismissed_reason=None,
        )


def test_record_blocks_safe_for_action_drafts_true() -> None:
    """CLAUDE.md §2 — kaartjes blijven advies, geen auto-promotie."""

    with pytest.raises(ValueError, match="safe_for_action_drafts"):
        SellSignalCardRecord(
            card_id="c",
            ibkr_account_ref="paper",
            symbol="AAPL",
            currency="USD",
            signal_kind=SELL_SIGNAL_KIND_TAKE_PROFIT,
            action=SELL_SIGNAL_ACTION_SUGGEST_SELL,
            entry_price=Decimal("100"),
            current_price=Decimal("105"),
            quantity=10,
            current_pct_return=Decimal("5"),
            target_pct=Decimal("4"),
            target_reached=True,
            days_held=None,
            forecast_id=None,
            forecaster_above_target=None,
            position_in_loss=None,
            short_term_p50=None,
            short_term_horizon_days=None,
            short_term_prob_above_pct=None,
            expected_net_proceeds_eur=None,
            headline_nl="x",
            detail_nl="x",
            first_generated_at=_EVAL_AT,
            last_evaluated_at=_EVAL_AT,
            dismissed_at=None,
            dismissed_reason=None,
            safe_for_action_drafts=True,  # forbidden
        )


# ----------------------------------------------------------------------
# Upsert behavior
# ----------------------------------------------------------------------


def test_upsert_inserts_new_card(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemySellSignalCardRepository(connection, _readiness())
    result = repo.upsert(_take_profit_request())
    assert result.accepted
    assert result.record_id is not None
    all_cards = repo.list_all(ibkr_account_ref="paper")
    assert len(all_cards.records) == 1
    assert all_cards.records[0].symbol == "AAPL"
    assert all_cards.records[0].action == SELL_SIGNAL_ACTION_SUGGEST_SELL
    assert all_cards.records[0].dismissed_at is None


def test_upsert_updates_existing_card_preserving_first_generated_at(
    connection,  # type: ignore[no-untyped-def]
) -> None:
    repo = SqlAlchemySellSignalCardRepository(connection, _readiness())
    first = _take_profit_request(current_price="104.50")
    repo.upsert(first)
    initial = repo.list_all(ibkr_account_ref="paper").records[0]
    first_gen = initial.first_generated_at

    # Run again with newer evaluated_at; first_generated_at preserved.
    later = _take_profit_request(
        current_price="105",
        evaluated_at=_EVAL_AT.replace(hour=11),
    )
    repo.upsert(later)
    after = repo.list_all(ibkr_account_ref="paper").records[0]
    assert after.first_generated_at == first_gen
    assert after.last_evaluated_at > first_gen
    assert after.current_price == Decimal("105")


def test_dismiss_sets_dismissed_at(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemySellSignalCardRepository(connection, _readiness())
    request = _take_profit_request()
    repo.upsert(request)
    card = repo.list_all(ibkr_account_ref="paper").records[0]
    repo.dismiss(
        card_id=card.card_id,
        dismissed_at=_EVAL_AT.replace(hour=11),
        reason="ik wacht",
    )
    updated = repo.get(card_id=card.card_id)
    assert updated is not None
    assert updated.dismissed_at is not None
    assert updated.dismissed_reason == "ik wacht"
    # list_active excludes dismissed.
    assert repo.list_active(ibkr_account_ref="paper").records == ()


def test_upsert_preserves_dismissal_when_signal_unchanged(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemySellSignalCardRepository(connection, _readiness())
    repo.upsert(_take_profit_request())
    card = repo.list_all(ibkr_account_ref="paper").records[0]
    repo.dismiss(card_id=card.card_id, dismissed_at=_EVAL_AT.replace(hour=11))
    # Re-sweep with same action — dismissal stays.
    repo.upsert(
        _take_profit_request(
            current_price="106", evaluated_at=_EVAL_AT.replace(hour=12)
        )
    )
    after = repo.get(card_id=card.card_id)
    assert after is not None
    assert after.dismissed_at is not None


def test_upsert_clears_dismissal_when_reset_flag_set(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemySellSignalCardRepository(connection, _readiness())
    repo.upsert(_take_profit_request())
    card = repo.list_all(ibkr_account_ref="paper").records[0]
    repo.dismiss(card_id=card.card_id, dismissed_at=_EVAL_AT.replace(hour=11))

    # Sweep tells the repo the signal materially changed.
    repo.upsert(
        _take_profit_request(
            current_price="106",
            evaluated_at=_EVAL_AT.replace(hour=12),
            reset_dismissal=True,
        )
    )
    after = repo.get(card_id=card.card_id)
    assert after is not None
    assert after.dismissed_at is None
    assert after.dismissed_reason is None


def test_delete_for_position_removes_all_kinds(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemySellSignalCardRepository(connection, _readiness())
    repo.upsert(_take_profit_request(symbol="AAPL"))
    repo.upsert(
        SaveSellSignalCardRequest(
            card_id=f"sscv_{uuid4().hex}",
            ibkr_account_ref="paper",
            symbol="AAPL",
            currency="USD",
            signal_kind=SELL_SIGNAL_KIND_HOLD_REVIEW,
            action=SELL_SIGNAL_ACTION_HOLD,
            entry_price=Decimal("100"),
            current_price=Decimal("103"),
            quantity=100,
            current_pct_return=Decimal("3"),
            target_pct=Decimal("4"),
            target_reached=None,
            days_held=200,
            forecast_id="fc_y",
            forecaster_above_target=True,
            position_in_loss=False,
            short_term_p50=Decimal("110"),
            short_term_horizon_days=90,
            short_term_prob_above_pct=Decimal("60"),
            expected_net_proceeds_eur=None,
            headline_nl="x",
            detail_nl="y",
            evaluated_at=_EVAL_AT,
        )
    )
    assert len(repo.list_all(ibkr_account_ref="paper").records) == 2
    repo.delete_for_position(ibkr_account_ref="paper", symbol="AAPL")
    assert repo.list_all(ibkr_account_ref="paper").records == ()


def test_list_active_filters_to_suggest_sell_only(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemySellSignalCardRepository(connection, _readiness())
    repo.upsert(_take_profit_request(action=SELL_SIGNAL_ACTION_SUGGEST_SELL))
    repo.upsert(_take_profit_request(symbol="MSFT", action=SELL_SIGNAL_ACTION_HOLD))
    active = repo.list_active(ibkr_account_ref="paper")
    assert len(active.records) == 1
    assert active.records[0].symbol == "AAPL"
