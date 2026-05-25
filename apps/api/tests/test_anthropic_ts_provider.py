"""Tests for the V1.1 Slice 30 real Anthropic Claude TS provider."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from ai_trading_agent_storage import ClaudeAiBudgetUsageRecord
from portfolio_outlook_portfolio import (
    HistoricalBar,
    TsModelProviderInputs,
    TsModelProviderResult,
    TsModelProviderUnavailable,
)

from portfolio_outlook_api.anthropic_ts_provider import (
    PROVIDER_CODE,
    TS_TOOL_NAME,
    AnthropicTsModelProvider,
)

# ---- Fake Anthropic client (tool-use response) -------------------------


@dataclass
class _FakeToolUseBlock:
    type: str = "tool_use"
    name: str = TS_TOOL_NAME
    input: dict[str, Any] | None = None


@dataclass
class _FakeUsage:
    input_tokens: int = 400
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 120


@dataclass
class _FakeMessage:
    content: list[_FakeToolUseBlock]
    usage: _FakeUsage
    model: str = "claude-haiku-4-5-20251001"


class _FakeMessagesAPI:
    def __init__(
        self,
        *,
        tool_input: dict[str, Any] | None,
        usage: _FakeUsage | None = None,
        raises: Exception | None = None,
        tool_name: str = TS_TOOL_NAME,
    ) -> None:
        self._tool_input = tool_input
        self._usage = usage or _FakeUsage()
        self._raises = raises
        self._tool_name = tool_name
        self.last_payload: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> _FakeMessage:
        self.last_payload = kwargs
        if self._raises is not None:
            raise self._raises
        return _FakeMessage(
            content=[
                _FakeToolUseBlock(name=self._tool_name, input=self._tool_input),
            ],
            usage=self._usage,
        )


class _FakeAnthropicClient:
    def __init__(self, *, messages: _FakeMessagesAPI) -> None:
        self.messages = messages


class _FakeBudgetRepo:
    def __init__(self, *, monthly_total: Decimal = Decimal("0")) -> None:
        self._monthly_total = monthly_total
        self.saved: list[ClaudeAiBudgetUsageRecord] = []

    def monthly_total_eur(self, budget_month: str) -> Decimal:
        return self._monthly_total

    def save_usage(self, record):  # type: ignore[no-untyped-def]
        self.saved.append(record)


def _bars(closes: list[float]) -> list[HistoricalBar]:
    return [
        HistoricalBar(
            bar_date=date(2024, 1, 1) + timedelta(days=i),
            close_price=Decimal(str(c)),
        )
        for i, c in enumerate(closes)
    ]


def _inputs(**overrides: Any) -> TsModelProviderInputs:
    base = dict(
        historical_bars=_bars([100.0 + 0.1 * i for i in range(120)]),
        current_price=Decimal("112.0"),
        horizon_trading_days=21,
        asset_symbol="AAPL",
        sector="Technology",
    )
    base.update(overrides)
    return TsModelProviderInputs(**base)


def _valid_tool_input() -> dict[str, Any]:
    return {
        "p10_price": 105.0,
        "p50_price": 115.0,
        "p90_price": 125.0,
        "prob_gain": 0.62,
        "expected_return_pct": 3.0,
        "confidence_score": 0.55,
        "explanation_nl": "Voorspelling op basis van 120 bars.",
    }


def _make_provider(
    *,
    tool_input: dict[str, Any] | None = None,
    raises: Exception | None = None,
    tool_name: str = TS_TOOL_NAME,
    monthly_total: Decimal = Decimal("0"),
    monthly_cap: Decimal = Decimal("50"),
) -> tuple[AnthropicTsModelProvider, _FakeMessagesAPI, _FakeBudgetRepo]:
    if tool_input is None and raises is None:
        tool_input = _valid_tool_input()
    messages = _FakeMessagesAPI(
        tool_input=tool_input, raises=raises, tool_name=tool_name
    )
    client = _FakeAnthropicClient(messages=messages)
    repo = _FakeBudgetRepo(monthly_total=monthly_total)
    provider = AnthropicTsModelProvider(
        budget_repo=repo,
        monthly_cap_eur=monthly_cap,
        client_factory=lambda: client,
    )
    return provider, messages, repo


# ---- happy path --------------------------------------------------------


def test_forecast_returns_typed_result_and_persists_audit_row() -> None:
    provider, messages, repo = _make_provider()
    result = provider.forecast(_inputs())
    assert isinstance(result, TsModelProviderResult)
    assert result.p10_price == Decimal("105.000000")
    assert result.p50_price == Decimal("115.000000")
    assert result.p90_price == Decimal("125.000000")
    assert result.prob_gain == Decimal("0.620000")
    assert result.model_provider_code == PROVIDER_CODE
    # One audit row was persisted with the ts_forecast call_kind.
    assert len(repo.saved) == 1
    assert repo.saved[0].call_kind == "ts_forecast"
    assert repo.saved[0].safe_for_action_drafts is False
    assert repo.saved[0].safe_for_orders is False


def test_forecast_sends_tool_use_call_with_locked_schema() -> None:
    provider, messages, _ = _make_provider()
    provider.forecast(_inputs())
    payload = messages.last_payload
    assert payload is not None
    # The provider forces the model to call the locked tool.
    tools = payload["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == TS_TOOL_NAME
    assert payload["tool_choice"] == {"type": "tool", "name": TS_TOOL_NAME}
    # System prompt cached for the day.
    system_blocks = payload["system"]
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_forecast_user_payload_includes_symbol_and_horizon() -> None:
    provider, messages, _ = _make_provider()
    provider.forecast(_inputs(asset_symbol="MSFT", horizon_trading_days=42))
    payload = messages.last_payload
    user_text = payload["messages"][0]["content"]
    assert "MSFT" in user_text
    assert "Horizon (handelsdagen): 42" in user_text


# ---- budget cap --------------------------------------------------------


def test_forecast_returns_unavailable_when_budget_exceeded() -> None:
    provider, _, repo = _make_provider(monthly_total=Decimal("60"))
    result = provider.forecast(_inputs())
    assert isinstance(result, TsModelProviderUnavailable)
    assert result.reason == "budget_exceeded"
    # No audit row should have been written.
    assert repo.saved == []


# ---- malformed responses -----------------------------------------------


def test_forecast_returns_provider_error_when_tool_payload_missing() -> None:
    """Model didn't call the locked tool — should map cleanly to
    provider_error so the AiTsPredictor blocks."""

    provider, _, repo = _make_provider(tool_name="wrong_tool")
    result = provider.forecast(_inputs())
    assert isinstance(result, TsModelProviderUnavailable)
    assert result.reason == "provider_error"
    # No audit row — the cost path is gated on a valid payload.
    assert repo.saved == []


def test_forecast_returns_provider_error_when_quantiles_unordered() -> None:
    bad_input = _valid_tool_input()
    bad_input["p10_price"] = 200.0  # higher than p50
    provider, _, _ = _make_provider(tool_input=bad_input)
    result = provider.forecast(_inputs())
    assert isinstance(result, TsModelProviderUnavailable)
    assert result.reason == "provider_error"


def test_forecast_returns_provider_error_when_prob_gain_out_of_range() -> None:
    bad_input = _valid_tool_input()
    bad_input["prob_gain"] = 1.5
    provider, _, _ = _make_provider(tool_input=bad_input)
    result = provider.forecast(_inputs())
    assert isinstance(result, TsModelProviderUnavailable)
    assert result.reason == "provider_error"


def test_forecast_returns_provider_error_when_sdk_raises() -> None:
    provider, _, _ = _make_provider(raises=RuntimeError("kaboom"))
    result = provider.forecast(_inputs())
    assert isinstance(result, TsModelProviderUnavailable)
    assert result.reason == "provider_error"
    assert "kaboom" in result.detail_nl


# ---- factory gates -----------------------------------------------------


def test_factory_returns_stub_when_code_is_stub() -> None:
    from portfolio_outlook_api.ai_ts_provider import (
        StubTsModelProvider,
        build_ts_model_provider,
    )
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_ts_predictor_enabled = True
    s.ai_ts_predictor_provider_code = "stub"
    provider = build_ts_model_provider(s)
    assert isinstance(provider, StubTsModelProvider)


def test_factory_unavailable_when_anthropic_key_missing() -> None:
    from portfolio_outlook_api.ai_ts_provider import build_ts_model_provider
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_ts_predictor_enabled = True
    s.ai_ts_predictor_real_client_enabled = True
    s.ai_ts_predictor_provider_code = "anthropic_claude"
    s.claude_ai_api_key = None
    out = build_ts_model_provider(
        s, budget_repo=_FakeBudgetRepo(), invoked_from_scheduler=True
    )
    assert isinstance(out, TsModelProviderUnavailable)
    assert out.reason == "claude_ai_api_key_missing"


def test_factory_unavailable_when_budget_repo_missing() -> None:
    from portfolio_outlook_api.ai_ts_provider import build_ts_model_provider
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_ts_predictor_enabled = True
    s.ai_ts_predictor_real_client_enabled = True
    s.ai_ts_predictor_provider_code = "anthropic_claude"
    s.claude_ai_api_key = "sk-test"
    out = build_ts_model_provider(s, budget_repo=None, invoked_from_scheduler=True)
    assert isinstance(out, TsModelProviderUnavailable)
    assert out.reason == "claude_ai_budget_repo_missing"


def test_factory_unavailable_on_ad_hoc_call_when_daily_only_locked() -> None:
    from portfolio_outlook_api.ai_ts_provider import build_ts_model_provider
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_ts_predictor_enabled = True
    s.ai_ts_predictor_real_client_enabled = True
    s.ai_ts_predictor_provider_code = "anthropic_claude"
    s.claude_ai_api_key = "sk-test"
    s.ai_ts_predictor_daily_only = True
    # invoked_from_scheduler defaults to False → blocked.
    out = build_ts_model_provider(s, budget_repo=_FakeBudgetRepo())
    assert isinstance(out, TsModelProviderUnavailable)
    assert out.reason == "daily_only_invocation_required"


def test_factory_returns_real_provider_when_all_gates_open() -> None:
    from portfolio_outlook_api.ai_ts_provider import build_ts_model_provider
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_ts_predictor_enabled = True
    s.ai_ts_predictor_real_client_enabled = True
    s.ai_ts_predictor_provider_code = "anthropic_claude"
    s.claude_ai_api_key = "sk-test"
    s.ai_ts_predictor_daily_only = True
    out = build_ts_model_provider(
        s, budget_repo=_FakeBudgetRepo(), invoked_from_scheduler=True
    )
    assert isinstance(out, AnthropicTsModelProvider)


def test_factory_timesfm_returns_unavailable_with_stable_reason() -> None:
    from portfolio_outlook_api.ai_ts_provider import build_ts_model_provider
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_ts_predictor_enabled = True
    s.ai_ts_predictor_real_client_enabled = True
    s.ai_ts_predictor_provider_code = "timesfm"
    out = build_ts_model_provider(s)
    assert isinstance(out, TsModelProviderUnavailable)
    assert out.reason == "timesfm_not_implemented"


def test_factory_other_code_returns_real_client_not_implemented() -> None:
    from portfolio_outlook_api.ai_ts_provider import build_ts_model_provider
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_ts_predictor_enabled = True
    s.ai_ts_predictor_real_client_enabled = True
    s.ai_ts_predictor_provider_code = "chronos"
    out = build_ts_model_provider(s)
    assert isinstance(out, TsModelProviderUnavailable)
    assert out.reason == "real_client_not_implemented"
