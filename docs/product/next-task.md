# Task 184

Slice 29 — V1.1 real AI explanation provider. Replaces the
existing Slice 10 stub Anthropic Claude explanation provider with
a real HTTP client honouring the §22.2 monthly budget cap.

Scope:
- New `apps/api` module `anthropic_explanation_provider.py`
  wrapping the official `anthropic` SDK. Implements the existing
  Slice 10 `ExplanationProviderProtocol`. Uses Claude Haiku by
  default (cheapest tier suitable for paraphrase tasks).
- **Mandatory prompt caching**: the locked Dutch system prompt +
  the deterministic legal disclaimer use Anthropic ephemeral
  cache breakpoints so the per-call cost stays at the cache-hit
  rate. The Research Desk evidence summaries are also cached
  per-day so the morning chain pays the full input cost once.
- **Budget enforcement**: a new
  `apps/api/src/portfolio_outlook_api/claude_ai_budget.py` module
  tracks per-month total token cost in a tiny audit table
  `claude_ai_budget_usage` (storage migration `0043`). The
  provider checks the running total before each call; once the
  total exceeds `CLAUDE_AI_BUDGET_MONTHLY_EUR` the provider
  raises `ClaudeAiBudgetExceededError` and the orchestrator falls
  back to the stub. The audit row persists usage per
  (day, provider_code, input_tokens, output_tokens) so the
  operator can see exactly when the budget runs out.
- New settings: `claude_ai_explanation_model` (default
  `claude-haiku-4-5-20251001`), `claude_ai_api_key` (env-only;
  no committed default).
- Factory `build_explanation_provider(settings)` returns the real
  client when `claude_ai_explanation_real_client_enabled=true`
  AND the API key is set, otherwise the stub (V1 behaviour).
- Hallucinated-number guard stays from Slice 10 — the real
  client's output still goes through the same validation pass;
  any number not in the source Decision Package fails.
- Tests cover: budget cap blocks the real call when the running
  total exceeds the threshold; cache-breakpoint markers in the
  prompt; factory gates (key missing / flag off / both set);
  hallucinated-number guard still fires on the real response.

Manual approval gate stays; safety booleans hard-False; AI never
originates a number.

When Slice 29 ships, Slice 30 (real AI TS predictor) is
unblocked.
