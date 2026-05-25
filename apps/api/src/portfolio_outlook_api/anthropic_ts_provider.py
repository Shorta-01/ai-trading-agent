"""Real Anthropic Claude time-series forecast provider (V1.1 Slice 30).

Replaces the Slice 18 ``StubTsModelProvider`` for the AI vote in
the ensemble. Uses Anthropic's tool-use (structured output) so the
response is forced into the locked
:class:`TsModelProviderResult` shape: a malformed response is
caught at the boundary and translated into
:class:`TsModelProviderUnavailable("provider_error")` so the
predictor (already from Slice 18) blocks cleanly rather than
hallucinating.

Budget enforcement re-uses the Slice 29 ``claude_ai_budget`` module
— the per-call cost lands in the same
``claude_ai_budget_usage`` audit table under ``call_kind="ts_forecast"``.
The monthly cap is shared across explanation + TS calls so the
operator can't blow the budget by routing through a second
provider.

§22.2 daily-only invocation: the provider is wired through the
scheduler-driven morning chain only. The factory inspects
``ai_ts_predictor_daily_only`` so the operator can flag the
provider as "only callable during the daily fire"; the
orchestrator enforces it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from decimal import Decimal
from typing import Any, Final, Protocol

from portfolio_outlook_portfolio import (
    TsModelProviderInputs,
    TsModelProviderResult,
    TsModelProviderUnavailable,
)

from portfolio_outlook_api.claude_ai_budget import (
    CallCostBreakdown,
    ClaudeAiBudgetExceededError,
    assert_budget_available,
    compute_cost_eur,
    persist_call_cost,
)

PROVIDER_CODE: Final[str] = "anthropic_claude"
DEFAULT_MODEL_NAME: Final[str] = "claude-haiku-4-5-20251001"
TS_TOOL_NAME: Final[str] = "emit_ts_forecast"

# Locked Dutch system prompt — cached on every call.
SYSTEM_PROMPT_NL: Final[str] = (
    "Je bent een numerieke time-series voorspeller voor een Nederlandstalig "
    "trading-dashboard. Voor elke vraag krijg je een historische "
    "prijsreeks + de huidige prijs + een horizon in handelsdagen. Geef "
    "een lognormale-achtige verdeling terug door de tool "
    f"`{TS_TOOL_NAME}` aan te roepen. Verzin geen getallen die niet uit "
    "de input volgen. Geef geen advies. Houd quantielen in volgorde: "
    "p10 ≤ p50 ≤ p90. Houd `prob_gain` ∈ [0, 1]. Houd "
    "`confidence_score` ∈ [0, 1] en lager wanneer de input dun is."
)

# JSON schema the tool-use call must conform to. Mirrors the locked
# TsModelProviderResult shape exactly.
TS_TOOL_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "p10_price": {"type": "number"},
        "p50_price": {"type": "number"},
        "p90_price": {"type": "number"},
        "prob_gain": {"type": "number", "minimum": 0, "maximum": 1},
        "expected_return_pct": {"type": "number"},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
        "explanation_nl": {"type": "string"},
    },
    "required": [
        "p10_price",
        "p50_price",
        "p90_price",
        "prob_gain",
        "expected_return_pct",
        "confidence_score",
        "explanation_nl",
    ],
}


class _BudgetRepoProtocol(Protocol):
    def monthly_total_eur(self, budget_month: str) -> Decimal: ...

    def save_usage(self, record: Any) -> object: ...


class _AnthropicMessageProtocol(Protocol):
    content: list[Any]
    usage: Any
    model: str


class _AnthropicMessagesAPI(Protocol):
    def create(self, **kwargs: Any) -> _AnthropicMessageProtocol: ...


class _AnthropicClientProtocol(Protocol):
    messages: _AnthropicMessagesAPI


def _decimal(value: float | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))


def _extract_tool_call(message: _AnthropicMessageProtocol) -> dict[str, Any] | None:
    """Pull the structured-output tool_use payload from an Anthropic
    Message. Returns the first ``tool_use`` block's ``input`` dict, or
    ``None`` if the model didn't call the locked tool (a
    malformed response).
    """

    for block in message.content:
        block_type = getattr(block, "type", None)
        if block_type == "tool_use" and getattr(block, "name", None) == TS_TOOL_NAME:
            payload = getattr(block, "input", None)
            if isinstance(payload, dict):
                return payload
            # Some SDK variants store the input as a JSON string; be
            # robust to that.
            if isinstance(payload, str):
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError:
                    return None
                if isinstance(parsed, dict):
                    return parsed
    return None


def _validate_payload(payload: dict[str, Any]) -> str | None:
    """Validate the structured-output payload against the locked
    schema. Returns ``None`` on pass, a stable Dutch failure string
    on miss."""

    required = TS_TOOL_SCHEMA["required"]
    for key in required:
        if key not in payload:
            return f"ontbrekend veld `{key}`"
    try:
        p10 = float(payload["p10_price"])
        p50 = float(payload["p50_price"])
        p90 = float(payload["p90_price"])
    except (TypeError, ValueError):
        return "quantielen zijn geen getallen"
    if not (p10 <= p50 <= p90):
        return f"quantielen niet in volgorde (p10={p10}, p50={p50}, p90={p90})"
    try:
        prob_gain = float(payload["prob_gain"])
    except (TypeError, ValueError):
        return "prob_gain is geen getal"
    if not (0.0 <= prob_gain <= 1.0):
        return f"prob_gain={prob_gain} valt buiten [0, 1]"
    try:
        confidence = float(payload["confidence_score"])
    except (TypeError, ValueError):
        return "confidence_score is geen getal"
    if not (0.0 <= confidence <= 1.0):
        return f"confidence_score={confidence} valt buiten [0, 1]"
    return None


def _build_messages_payload(
    *,
    inputs: TsModelProviderInputs,
    model_name: str,
    max_tokens: int,
) -> dict[str, Any]:
    bars_text = "\n".join(
        f"{bar.bar_date.isoformat()}: {float(bar.close_price):.4f}"
        for bar in inputs.historical_bars[-60:]
    )
    user_text = (
        f"Symbol: {inputs.asset_symbol}\n"
        f"Sector: {inputs.sector or 'onbekend'}\n"
        f"Huidige prijs: {float(inputs.current_price):.4f}\n"
        f"Horizon (handelsdagen): {inputs.horizon_trading_days}\n\n"
        f"Laatste {min(60, len(inputs.historical_bars))} bars (datum: close):\n"
        f"{bars_text}\n\n"
        f"Roep de tool `{TS_TOOL_NAME}` aan met de voorspelling."
    )
    return {
        "model": model_name,
        "max_tokens": max_tokens,
        "system": [
            {
                "type": "text",
                "text": SYSTEM_PROMPT_NL,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "tools": [
            {
                "name": TS_TOOL_NAME,
                "description": (
                    "Geef de quantiel-distributie van de toekomstige prijs, "
                    "de probabiliteit op winst, het verwachte rendement en "
                    "een Dutch toelichting."
                ),
                "input_schema": TS_TOOL_SCHEMA,
            }
        ],
        "tool_choice": {"type": "tool", "name": TS_TOOL_NAME},
        "messages": [{"role": "user", "content": user_text}],
    }


class AnthropicTsModelProvider:
    """V1.1 §22.2 real Claude numerical-forecast provider.

    Implements the ``forecast`` method expected by the Slice 18
    ``AiTsPredictor``. Budget cap + audit log share the Slice 29
    ``claude_ai_budget`` module.
    """

    def __init__(
        self,
        *,
        budget_repo: _BudgetRepoProtocol,
        monthly_cap_eur: Decimal,
        model_name: str = DEFAULT_MODEL_NAME,
        max_tokens: int = 1024,
        client_factory: Callable[[], _AnthropicClientProtocol] | None = None,
    ) -> None:
        self._budget_repo = budget_repo
        self._monthly_cap_eur = monthly_cap_eur
        self._model_name = model_name
        self._max_tokens = max_tokens
        self._client_factory = client_factory

    @property
    def model_name(self) -> str:
        return self._model_name

    def _build_client(self) -> _AnthropicClientProtocol:
        if self._client_factory is not None:
            return self._client_factory()
        from typing import cast

        from anthropic import Anthropic

        return cast(_AnthropicClientProtocol, Anthropic())

    def forecast(
        self, inputs: TsModelProviderInputs
    ) -> TsModelProviderResult | TsModelProviderUnavailable:
        """Issue one tool-use call to Claude, validate the response,
        persist the audit row, and return a typed result.

        Returns ``TsModelProviderUnavailable`` rather than raising on
        soft errors (provider returned nothing useful, payload failed
        validation, budget exceeded) — the predictor handles all of
        these cleanly via its existing ``status=blocked`` path.
        """

        try:
            assert_budget_available(
                repo=self._budget_repo, monthly_cap_eur=self._monthly_cap_eur
            )
        except ClaudeAiBudgetExceededError as exc:
            return TsModelProviderUnavailable(
                reason="budget_exceeded",
                detail_nl=str(exc),
            )

        payload = _build_messages_payload(
            inputs=inputs,
            model_name=self._model_name,
            max_tokens=self._max_tokens,
        )
        try:
            client = self._build_client()
            message = client.messages.create(**payload)
        except Exception as exc:  # noqa: BLE001 — provider boundary
            return TsModelProviderUnavailable(
                reason="provider_error",
                detail_nl=f"Anthropic SDK gaf een fout: {exc}",
            )

        tool_payload = _extract_tool_call(message)
        if tool_payload is None:
            return TsModelProviderUnavailable(
                reason="provider_error",
                detail_nl="Anthropic-response bevat geen geldige tool_use call.",
            )
        validation_error = _validate_payload(tool_payload)
        if validation_error is not None:
            return TsModelProviderUnavailable(
                reason="provider_error",
                detail_nl=f"Tool-payload faalt validatie: {validation_error}.",
            )

        # Record usage + cost.
        usage = message.usage
        input_units = int(
            getattr(usage, "input_tokens", 0)
            + getattr(usage, "cache_creation_input_tokens", 0)
        )
        cached_input_units = int(getattr(usage, "cache_read_input_tokens", 0))
        output_units = int(getattr(usage, "output_tokens", 0))
        cost = compute_cost_eur(
            input_units=input_units,
            cached_input_units=cached_input_units,
            output_units=output_units,
        )
        persist_call_cost(
            repo=self._budget_repo,
            provider_code=PROVIDER_CODE,
            model_name=self._model_name,
            call_kind="ts_forecast",
            breakdown=CallCostBreakdown(
                input_units=input_units,
                cached_input_units=cached_input_units,
                output_units=output_units,
                cost_eur=cost,
            ),
            explanation_nl=(
                f"Anthropic Claude TS-forecast voor {inputs.asset_symbol} "
                f"({inputs.horizon_trading_days}d); €{cost:.4f}."
            ),
        )

        return TsModelProviderResult(
            p10_price=_decimal(tool_payload["p10_price"]),
            p50_price=_decimal(tool_payload["p50_price"]),
            p90_price=_decimal(tool_payload["p90_price"]),
            prob_gain=_decimal(tool_payload["prob_gain"]),
            expected_return_pct=_decimal(tool_payload["expected_return_pct"]),
            confidence_score=_decimal(tool_payload["confidence_score"]),
            model_provider_code=PROVIDER_CODE,
            model_name=getattr(message, "model", self._model_name),
            model_version="v1.1-anthropic-2026-05",
            explanation_nl=str(tool_payload["explanation_nl"]),
        )


__all__ = [
    "DEFAULT_MODEL_NAME",
    "PROVIDER_CODE",
    "SYSTEM_PROMPT_NL",
    "TS_TOOL_NAME",
    "TS_TOOL_SCHEMA",
    "AnthropicTsModelProvider",
]
