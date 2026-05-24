# Task 173

Slice 18 — AI foundation TS-model predictor. Fifth and final concrete
step of the V1 §21.4 ensemble lock. Plugs an AI time-series model into
the predictor protocol behind the same gate pattern as Slice 10's
explanation provider.

Scope:
- New `ai_ts_predictor` module in `apps/api` with:
  * `TsModelProviderInputs` (bars + horizon + asset metadata) and
    `TsModelProviderResult` (p10/p50/p90 + prob_gain + explanation +
    model identity).
  * `TsModelProviderProtocol` with a single `forecast(inputs)` method.
  * `StubTsModelProvider` — deterministic Python: takes the last N
    bars, computes a small-sample empirical quantile + simple drift,
    returns a `TsModelProviderResult`. No AI runtime — keeps the
    boundary testable. Mirrors Slice 10's `StubExplanationProvider`
    pattern.
  * `build_ts_model_provider(settings)` factory: returns the stub
    when `ai_ts_predictor_enabled=True` + `ai_ts_predictor_provider_code="stub"`,
    otherwise returns an `Unavailable` reason. Real providers
    (TimesFM / Chronos / Lag-Llama) return
    `real_client_not_implemented` for V1.
- New pure-Python `AiTsPredictor` in `packages/portfolio` implementing
  `PredictorProtocol`: delegates to a provider (factory-injected),
  validates the result (numeric quantile ordering, prob_gain ∈ [0, 1]),
  and returns a `PredictionDistribution`. Gracefully degrades to
  ``status=blocked`` with `provider_unavailable` when the provider is
  not built.
- New settings: `ai_ts_predictor_enabled` (default `False`),
  `ai_ts_predictor_real_client_enabled` (default `False`),
  `ai_ts_predictor_provider_code` (default `"stub"`).
- Tests cover the protocol, the stub provider, the factory gates, the
  predictor's graceful-degrade path on provider unavailability, and
  the validation guards.

No orchestrator change yet; the AI predictor joins the ensemble when
Slice 19+ wires `forecast_sync` to compose all five predictors.
