# Task 185

Slice 30 — V1.1 real AI TS predictor. Last AI-provider slice;
replaces the Slice 18 `StubTsModelProvider` with a real Anthropic
Claude numerical-forecast client honouring the §22.2 budget cap.

Scope:
- New `apps/api/anthropic_ts_provider.py` implementing the
  `TsModelProviderProtocol` from
  `packages/portfolio/ai_ts_predictor.py`. The provider uses
  Anthropic's structured-output mode (tool-use returning JSON) so
  the prob_gain / quantile fields validate cleanly against the
  Slice 18 validator — any malformed response counts as
  ``provider_error`` and the AI predictor blocks rather than
  hallucinating.
- **Budget enforcement reuses Slice 29's
  `claude_ai_budget` module** — single call kind
  ``ts_forecast``; the per-call cost lands in the same
  `claude_ai_budget_usage` audit table so the monthly cap is
  shared across explanation + TS providers.
- **Daily-only invocation**: the factory returns the real client
  only when the scheduler-driven morning chain fires; on-demand
  TS predictions stay routed to the stub.
- Optional **TimesFM HTTP adapter** behind a `timesfm_enabled`
  flag (off by default; placeholder raises
  ``NotImplementedError`` until the operator wires a real
  TimesFM deployment).
- New settings:
  `ai_ts_predictor_provider_code` accepts a new
  `anthropic_claude` value alongside the existing `stub` /
  `timesfm` / `chronos` / `lag_llama`. A new
  `ai_ts_predictor_daily_only` flag (default True) enforces the
  daily-call invariant.
- Factory `build_ts_model_provider(settings, *, budget_repo)`
  returns the real client when the gates open
  (`ai_ts_predictor_real_client_enabled` AND
  `provider_code=anthropic_claude` AND key set AND budget_repo
  supplied), otherwise falls back to the stub or returns
  `TsModelProviderUnavailable`.
- Tests cover: structured-output round-trip with a fake client;
  budget cap blocks the call; validator catches malformed JSON;
  factory gates (key missing / budget_repo missing / daily-only
  enforced); TimesFM placeholder raises NotImplementedError.

Manual approval gate stays; safety booleans hard-False; AI is
still one vote in the ensemble, never authoritative.

When Slice 30 ships, Slice 31 (universe scan expansion +
operator-selectable set) is unblocked.
