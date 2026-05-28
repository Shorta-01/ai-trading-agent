"""AI time-series provider factory + stub (Slice 18) — apps/api side.

Mirrors the Slice 10 explanation-provider pattern:

* The deterministic stub produces a meaningful (empirical-quantile)
  forecast without invoking any AI runtime, so the boundary is
  testable.
* The factory returns the stub only when the operator explicitly opts
  in via settings.
* Real providers (TimesFM / Chronos / Lag-Llama / Anthropic
  forecasting) return :class:`TsModelProviderUnavailable` with
  ``real_client_not_implemented`` until a future slice plugs them in.

The actual predictor (`AiTsPredictor`) lives in `packages/portfolio` so
this package can stay stdlib-only.
"""

from __future__ import annotations

import math
import statistics
from decimal import Decimal
from typing import Final

from portfolio_outlook_portfolio import (
    TsModelProviderInputs,
    TsModelProviderResult,
    TsModelProviderUnavailable,
)

from portfolio_outlook_api.config import Settings

STUB_PROVIDER_CODE: Final[str] = "stub"
STUB_MODEL_NAME: Final[str] = "empirical_quantile_drift"
STUB_MODEL_VERSION: Final[str] = "v1"

# Same horizon-trading-days assumption used elsewhere.
DEFAULT_TRADING_DAYS_PER_YEAR: Final[int] = 252


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))


def _prob(value: float) -> Decimal:
    bounded = max(0.0, min(1.0, value))
    return _money(bounded)


def _decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))


class StubTsModelProvider:
    """Deterministic-Python forecaster — no AI runtime.

    The "model" is intentionally simple but defensible:

    * Compute log-returns over the supplied bars.
    * Mean of recent returns is the drift; population SD is the
      volatility.
    * Project drift + volatility onto the requested horizon to form a
      lognormal distribution; emit p10/p50/p90 + prob_gain.

    This is not a real AI runtime — it exists purely so the
    ``TsModelProviderProtocol`` boundary has a default implementation
    that lets the predictor + ensemble run offline. Real TimesFM /
    Chronos / Lag-Llama providers will replace this when wired in a
    future slice.
    """

    def __init__(
        self,
        *,
        recent_window: int = 120,
        trading_days_per_year: int = DEFAULT_TRADING_DAYS_PER_YEAR,
    ) -> None:
        self._recent_window = recent_window
        self._trading_days_per_year = trading_days_per_year

    def forecast(self, inputs: TsModelProviderInputs) -> TsModelProviderResult:
        prices = [float(bar.close_price) for bar in inputs.historical_bars]
        if len(prices) < 30 or inputs.current_price <= 0:
            current_float = float(inputs.current_price) if inputs.current_price > 0 else 0.000001
            return TsModelProviderResult(
                p10_price=_money(current_float * 0.97),
                p50_price=_money(current_float),
                p90_price=_money(current_float * 1.03),
                prob_gain=Decimal("0.500000"),
                expected_return_pct=Decimal("0.000000"),
                confidence_score=Decimal("0.100000"),
                model_provider_code=STUB_PROVIDER_CODE,
                model_name=STUB_MODEL_NAME,
                model_version=STUB_MODEL_VERSION,
                explanation_nl=(
                    "Stub TS-provider: te weinig bars voor een echte schatting; "
                    "neutrale distributie rond huidige prijs."
                ),
            )

        window = prices[-self._recent_window :] if len(prices) > self._recent_window else prices
        returns: list[float] = []
        for i in range(1, len(window)):
            prev = window[i - 1]
            curr = window[i]
            if prev > 0 and curr > 0:
                returns.append(math.log(curr / prev))
        if len(returns) < 5:
            current_float = float(inputs.current_price)
            return TsModelProviderResult(
                p10_price=_money(current_float * 0.97),
                p50_price=_money(current_float),
                p90_price=_money(current_float * 1.03),
                prob_gain=Decimal("0.500000"),
                expected_return_pct=Decimal("0.000000"),
                confidence_score=Decimal("0.100000"),
                model_provider_code=STUB_PROVIDER_CODE,
                model_name=STUB_MODEL_NAME,
                model_version=STUB_MODEL_VERSION,
                explanation_nl=(
                    "Stub TS-provider: te weinig log-returns; neutrale distributie."
                ),
            )

        mu = statistics.fmean(returns)
        sigma = statistics.pstdev(returns)
        horizon = inputs.horizon_trading_days
        horizon_drift = mu * horizon
        horizon_sd = sigma * math.sqrt(horizon) if sigma > 0 else 0.0001

        current = float(inputs.current_price)
        p10_log = horizon_drift + horizon_sd * (-1.2815515655446004)
        p50_log = horizon_drift
        p90_log = horizon_drift + horizon_sd * 1.2815515655446004
        p10 = current * math.exp(p10_log)
        p50 = current * math.exp(p50_log)
        p90 = current * math.exp(p90_log)
        # P(end > start) under the lognormal-with-drift assumption.
        z_for_zero = -horizon_drift / horizon_sd if horizon_sd > 0 else 0.0
        prob_gain = 1.0 - _normal_cdf(z_for_zero)
        expected_return_pct = (math.exp(p50_log) - 1.0) * 100.0

        # Confidence: more bars → more confident, capped at 0.85.
        sample_factor = min(1.0, len(returns) / 250.0)
        confidence = 0.4 + 0.45 * sample_factor

        return TsModelProviderResult(
            p10_price=_money(p10),
            p50_price=_money(p50),
            p90_price=_money(p90),
            prob_gain=_prob(prob_gain),
            expected_return_pct=_decimal(expected_return_pct),
            confidence_score=_decimal(confidence),
            model_provider_code=STUB_PROVIDER_CODE,
            model_name=STUB_MODEL_NAME,
            model_version=STUB_MODEL_VERSION,
            explanation_nl=(
                f"Stub TS-provider: empirisch p50={p50:.2f} over {horizon} dagen "
                f"(drift={mu:.5f}, sigma={sigma:.5f})."
            ),
        )


def build_ts_model_provider(
    runtime_settings: Settings,
    *,
    budget_repo: object | None = None,
    invoked_from_scheduler: bool = False,
) -> StubTsModelProvider | TsModelProviderUnavailable | object:
    """Return a provider or a :class:`TsModelProviderUnavailable` sentinel.

    Gates (every one must pass for the stub):
    - ``ai_ts_predictor_enabled``
    - ``ai_ts_predictor_provider_code == "stub"``

    ``provider_code="anthropic_claude"`` (an LLM directly producing forecasts —
    "case B") is **forbidden** by doctrine (``ai-usage.md`` §5 +
    ``forecast-engine.md`` §7) and always returns ``case_b_forbidden``. The
    path is removed, not flag-gated: no combination of API key / budget /
    feature flags can reach an LLM forecaster.

    Real TimesFM / Chronos / Lag-Llama providers still return
    ``real_client_not_implemented``; the operator surface is
    declared via the existing provider-code setting.

    ``budget_repo`` / ``invoked_from_scheduler`` are retained for signature
    stability (a future case-C feature-generator path would consume them).
    """

    if not runtime_settings.ai_ts_predictor_enabled:
        return TsModelProviderUnavailable(
            reason="ai_ts_predictor_disabled",
            detail_nl=(
                "AI TS-predictor is uitgeschakeld. Stel "
                "`AI_TS_PREDICTOR_ENABLED=true` in om hem te activeren."
            ),
        )
    code = (runtime_settings.ai_ts_predictor_provider_code or "").strip().lower()
    if code == STUB_PROVIDER_CODE:
        return StubTsModelProvider()
    if code == "anthropic_claude":
        # Case B — an LLM directly producing forecasts — is forbidden by
        # doctrine (ai-usage.md §5 + forecast-engine.md §7): "LLMs hallucinate
        # numbers; calibration is unreliable; risk is unbounded." The provider
        # is removed, not flag-gated: this return is reached before any
        # key/budget/flag check, so no configuration can instantiate an LLM
        # forecaster.
        return TsModelProviderUnavailable(
            reason="case_b_forbidden",
            detail_nl=(
                "LLM-als-voorspeller (case B) is verboden door de doctrine "
                "(ai-usage.md §5: LLMs hallucineren getallen, risico is "
                "onbegrensd). Gebruik `AI_TS_PREDICTOR_PROVIDER_CODE=stub`."
            ),
        )
    if not runtime_settings.ai_ts_predictor_real_client_enabled:
        return TsModelProviderUnavailable(
            reason="real_client_not_enabled",
            detail_nl=(
                "Echte AI TS-client is niet ingeschakeld. Gebruik "
                "`AI_TS_PREDICTOR_PROVIDER_CODE=stub` voor de deterministische "
                "fallback, of zet `AI_TS_PREDICTOR_REAL_CLIENT_ENABLED=true`."
            ),
        )
    if code == "timesfm":
        # V1.1 §22 placeholder — TimesFM HTTP wiring lands in a post-V1.1
        # widening once the operator points the deployment at a real
        # endpoint. The provider-code surface is declared from Slice 30
        # forward.
        return TsModelProviderUnavailable(
            reason="timesfm_not_implemented",
            detail_nl=(
                "TimesFM HTTP-adapter is gedeclareerd maar niet geïmplementeerd "
                "in V1.1; gebruik `anthropic_claude` of `stub`."
            ),
        )
    return TsModelProviderUnavailable(
        reason="real_client_not_implemented",
        detail_nl=(
            f"Provider `{code}` is nog niet geïmplementeerd in V1.1. "
            "Beschikbaar: `stub`, `anthropic_claude`."
        ),
    )


__all__ = [
    "STUB_PROVIDER_CODE",
    "STUB_MODEL_NAME",
    "STUB_MODEL_VERSION",
    "StubTsModelProvider",
    "build_ts_model_provider",
]
