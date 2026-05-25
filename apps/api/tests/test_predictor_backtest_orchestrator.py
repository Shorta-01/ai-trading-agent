"""Tests for the V1.1 predictor backtest orchestrator."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    MarketDataBarRecord,
    PredictorBacktestRunRecord,
)

from portfolio_outlook_api.predictor_backtest_orchestrator import (
    LOCKED_MODEL_CODES,
    SKIPPED_AI_TS_REASON,
    SKIPPED_QVM_REASON,
    run_backtest_for_symbol,
    serialize_backtest_run_record,
)


def _bar(d: int, close: str) -> MarketDataBarRecord:
    now = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=d + 1)
    return MarketDataBarRecord(
        bar_id=f"bar-{d}",
        ibkr_conid="265598",
        symbol="AAPL",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        provider_code="eodhd",
        bar_date=date(2024, 1, 1) + timedelta(days=d),
        interval_code="1day",
        open_price=Decimal(close),
        high_price=Decimal(close),
        low_price=Decimal(close),
        close_price=Decimal(close),
        adjusted_close_price=Decimal(close),
        volume=Decimal("1000"),
        provider_as_of=now,
        received_at=now,
        stored_at=now,
        source_type="provider",
        explanation_nl="test-fixture",
    )


class _FakeBarRepo:
    def __init__(self, bars):
        self._bars = bars

    def list_market_data_bars_by_conid(self, ibkr_conid, *, interval_code="1day", limit=750):
        class _Result:
            records = tuple(self._bars)

        return _Result()


class _FakeBacktestRepo:
    def __init__(self):
        self.saved: list[PredictorBacktestRunRecord] = []
        self.updated: list[PredictorBacktestRunRecord] = []

    def save_backtest_run(self, record):
        self.saved.append(record)

    def update_backtest_run(self, record):
        self.updated.append(record)


def _gen_uptrend_bars(count: int) -> list[MarketDataBarRecord]:
    return [
        _bar(d=i, close=f"{100.0 * math.exp(0.001 * i):.4f}")
        for i in range(count)
    ]


# ---- happy path: succeeded ----------------------------------------------


def test_orchestrator_runs_gbm_backtest_and_persists_succeeded() -> None:
    bar_repo = _FakeBarRepo(_gen_uptrend_bars(500))
    bt_repo = _FakeBacktestRepo()

    outcome = run_backtest_for_symbol(
        model_code="baseline_gbm",
        asset_symbol="AAPL",
        ibkr_conid="265598",
        bar_repo=bar_repo,
        backtest_repo=bt_repo,
        window_days=250,
        horizon_trading_days=21,
        step_days=10,
    )

    # Running row + terminal row persisted.
    assert len(bt_repo.saved) == 1
    assert bt_repo.saved[0].status == "running"
    assert len(bt_repo.updated) == 1
    assert bt_repo.updated[0].status == "succeeded"
    assert outcome.record.status == "succeeded"
    assert outcome.record.brier_score is not None
    assert outcome.record.hit_rate is not None


def test_orchestrator_runs_momentum_backtest() -> None:
    bar_repo = _FakeBarRepo(_gen_uptrend_bars(500))
    bt_repo = _FakeBacktestRepo()
    outcome = run_backtest_for_symbol(
        model_code="momentum_v1",
        asset_symbol="AAPL",
        ibkr_conid="265598",
        bar_repo=bar_repo,
        backtest_repo=bt_repo,
        window_days=260,  # momentum needs >=250
        horizon_trading_days=21,
        step_days=10,
    )
    assert outcome.record.model_code == "momentum_v1"
    assert outcome.record.status in {"succeeded", "skipped"}


# ---- deferred predictors --------------------------------------------------


def test_orchestrator_skips_qvm_with_stable_reason() -> None:
    bar_repo = _FakeBarRepo(_gen_uptrend_bars(500))
    bt_repo = _FakeBacktestRepo()
    outcome = run_backtest_for_symbol(
        model_code="qvm_factor_v1",
        asset_symbol="AAPL",
        ibkr_conid="265598",
        bar_repo=bar_repo,
        backtest_repo=bt_repo,
    )
    assert outcome.record.status == "skipped"
    assert outcome.record.blocking_reason == SKIPPED_QVM_REASON


def test_orchestrator_skips_ai_ts_with_stable_reason() -> None:
    bar_repo = _FakeBarRepo(_gen_uptrend_bars(500))
    bt_repo = _FakeBacktestRepo()
    outcome = run_backtest_for_symbol(
        model_code="ai_ts_v1",
        asset_symbol="AAPL",
        ibkr_conid="265598",
        bar_repo=bar_repo,
        backtest_repo=bt_repo,
    )
    assert outcome.record.status == "skipped"
    assert outcome.record.blocking_reason == SKIPPED_AI_TS_REASON


# ---- unknown model_code ---------------------------------------------------


def test_orchestrator_rejects_unknown_model_code_with_audit_row() -> None:
    bar_repo = _FakeBarRepo([])
    bt_repo = _FakeBacktestRepo()
    outcome = run_backtest_for_symbol(
        model_code="bogus_v1",
        asset_symbol="AAPL",
        ibkr_conid="265598",
        bar_repo=bar_repo,
        backtest_repo=bt_repo,
    )
    assert outcome.record.status == "skipped"
    assert outcome.record.blocking_reason == "unknown_model_code"
    # The initial save_backtest_run never fires because we short-circuit.
    assert len(bt_repo.saved) == 1
    assert bt_repo.saved[0].status == "skipped"


# ---- empty bars -----------------------------------------------------------


def test_orchestrator_skips_when_no_bars_persisted() -> None:
    bar_repo = _FakeBarRepo([])
    bt_repo = _FakeBacktestRepo()
    outcome = run_backtest_for_symbol(
        model_code="baseline_gbm",
        asset_symbol="AAPL",
        ibkr_conid="265598",
        bar_repo=bar_repo,
        backtest_repo=bt_repo,
    )
    assert outcome.record.status == "skipped"
    assert outcome.record.blocking_reason == "no_bars_persisted"


# ---- serialisation --------------------------------------------------------


def test_serialize_backtest_run_record_safety_booleans_are_false() -> None:
    bar_repo = _FakeBarRepo(_gen_uptrend_bars(500))
    bt_repo = _FakeBacktestRepo()
    outcome = run_backtest_for_symbol(
        model_code="baseline_gbm",
        asset_symbol="AAPL",
        ibkr_conid="265598",
        bar_repo=bar_repo,
        backtest_repo=bt_repo,
        window_days=250,
        horizon_trading_days=21,
        step_days=10,
    )
    payload = serialize_backtest_run_record(outcome.record)
    assert payload["safe_for_action_drafts"] is False
    assert payload["safe_for_orders"] is False
    assert payload["model_code"] == "baseline_gbm"
    assert payload["asset_symbol"] == "AAPL"
    assert payload["status"] == "succeeded"
    # Numeric fields are str (Decimal serialisation).
    assert isinstance(payload["brier_score"], str)
    assert isinstance(payload["hit_rate"], str)


def test_locked_model_codes_set_is_immutable() -> None:
    assert isinstance(LOCKED_MODEL_CODES, frozenset)
    assert "baseline_gbm" in LOCKED_MODEL_CODES
    assert "momentum_v1" in LOCKED_MODEL_CODES
    assert "mean_reversion_v1" in LOCKED_MODEL_CODES
    # QVM + AI TS deferred to later slices, not in the locked set.
    assert "qvm_factor_v1" not in LOCKED_MODEL_CODES
    assert "ai_ts_v1" not in LOCKED_MODEL_CODES
