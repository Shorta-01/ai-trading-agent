"""Unit tests for the alert-summary compose orchestrator.

The orchestrator wraps an explanation provider with the hallucination /
disclaimer / size guards. Hard contracts under test:

* When the provider is unavailable (budget cap, real-client off) the
  caller sees ``status="provider_unavailable"`` and ``summary_nl=None``
  so it can fall through to the deterministic template.
* When the AI tries to introduce a number that wasn't in the input
  evidence the output is blocked with ``hallucinated_numbers`` set.
* When the disclaimer is missing the output is blocked.
* When the alerts list is empty the orchestrator skips silently — no
  provider call is made.
"""

from __future__ import annotations

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_DISCLAIMER_MISSING,
    BLOCKING_REASON_HALLUCINATED_NUMBERS,
    EXPLANATION_STATUS_BLOCKED,
    EXPLANATION_STATUS_GENERATED,
    LOCKED_RISK_DISCLAIMER_NL,
)

from portfolio_outlook_api.ai_explanation_provider import (
    ExplanationProviderInputs,
    ExplanationProviderResult,
    ExplanationProviderUnavailable,
    StubExplanationProvider,
)
from portfolio_outlook_api.alert_summary_compose import (
    AlertSummaryResult,
    compose_alert_summary,
)


def test_stub_provider_produces_generated_summary() -> None:
    result = compose_alert_summary(
        kind="digest",
        context_text="Markt: EURONEXT. Datum: 2026-05-31. NAV verandering: 0.50% (EUR).",
        alert_lines=[
            "- [Hoog] NAV-daling: Portfolio NAV daalde met 2.5%.",
        ],
        provider=StubExplanationProvider(),
        max_output_chars=2000,
    )
    assert isinstance(result, AlertSummaryResult)
    assert result.status == EXPLANATION_STATUS_GENERATED
    assert result.summary_nl is not None
    assert LOCKED_RISK_DISCLAIMER_NL in result.summary_nl
    assert result.blocking_reason is None
    assert result.hallucinated_numbers == ()


def test_provider_unavailable_yields_none_summary() -> None:
    result = compose_alert_summary(
        kind="digest",
        context_text="X",
        alert_lines=["- [Hoog] X: Y"],
        provider=ExplanationProviderUnavailable(
            reason="budget_exceeded", detail_nl="Maandbudget overschreden."
        ),
        max_output_chars=2000,
    )
    assert result.status == "provider_unavailable"
    assert result.summary_nl is None
    assert result.blocking_reason == "budget_exceeded"


def test_empty_alerts_skips_without_calling_provider() -> None:
    class _ExplodingProvider:
        def generate(self, inputs: ExplanationProviderInputs) -> ExplanationProviderResult:
            raise AssertionError("provider must not be called for empty alerts")

    result = compose_alert_summary(
        kind="digest",
        context_text="X",
        alert_lines=[],
        provider=_ExplodingProvider(),
        max_output_chars=2000,
    )
    assert result.status == "skipped_no_alerts"
    assert result.summary_nl is None


def test_hallucinated_number_blocks_summary() -> None:
    class _HallucinatingProvider:
        def generate(self, inputs: ExplanationProviderInputs) -> ExplanationProviderResult:
            return ExplanationProviderResult(
                output_text=(
                    f"Vandaag doelprijs van 999 verwacht. {LOCKED_RISK_DISCLAIMER_NL}"
                ),
                model_provider_code="evil",
                model_name="x",
                model_version="v1",
            )

    result = compose_alert_summary(
        kind="digest",
        context_text="Markt: EURONEXT. NAV: 0.50%.",
        alert_lines=["- [Hoog] X: 2.5%"],
        provider=_HallucinatingProvider(),
        max_output_chars=2000,
    )
    assert result.status == EXPLANATION_STATUS_BLOCKED
    assert result.summary_nl is None
    assert result.blocking_reason == BLOCKING_REASON_HALLUCINATED_NUMBERS
    assert "999" in result.hallucinated_numbers


def test_missing_disclaimer_blocks_summary() -> None:
    class _NoDisclaimerProvider:
        def generate(self, inputs: ExplanationProviderInputs) -> ExplanationProviderResult:
            return ExplanationProviderResult(
                output_text="Vandaag een matige sessie. Geen disclaimer.",
                model_provider_code="stub",
                model_name="x",
                model_version="v1",
            )

    result = compose_alert_summary(
        kind="digest",
        context_text="X",
        alert_lines=["- [Hoog] X: Y"],
        provider=_NoDisclaimerProvider(),
        max_output_chars=2000,
    )
    assert result.status == EXPLANATION_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_DISCLAIMER_MISSING
    assert result.summary_nl is None


def test_provider_exception_classified_as_failed() -> None:
    class _RaisingProvider:
        def generate(self, inputs: ExplanationProviderInputs) -> ExplanationProviderResult:
            raise RuntimeError("model timeout")

    result = compose_alert_summary(
        kind="morning_alerts",
        context_text="X",
        alert_lines=["- [Hoog] X: Y"],
        provider=_RaisingProvider(),
        max_output_chars=2000,
    )
    assert result.status == "failed"
    assert result.blocking_reason == "provider_error"
    assert result.summary_nl is None
