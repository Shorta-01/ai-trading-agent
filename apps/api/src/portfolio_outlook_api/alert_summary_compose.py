"""AI-composed email summaries for digest + morning-alerts emails.

The deterministic template emails the worker sends today are always
shipped; this module adds an optional Dutch summary header at the top
that paraphrases what's already in the template. The same hallucination
guard the Decision Package explanation path uses
(:func:`validate_explanation_output`) applies here: the AI cannot
introduce a number that wasn't already in the deterministic template
body.

The orchestrator is intentionally not opinionated about *what* alerts
look like — it accepts the already-rendered Dutch template lines and
asks Claude to paraphrase them into a 2-3 sentence header. When the
provider is unavailable (budget cap hit, real client off, etc.) or the
output violates the guards, the caller falls through to template-only.

Hard contract: never originate a financial number; only paraphrase the
template the worker already composed. ``safe_for_orders`` is false for
the same reason every Slice-10 AI output is false — these summaries
guide attention, never execution.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from portfolio_outlook_portfolio import (
    EXPLANATION_STATUS_FAILED,
    EXPLANATION_STATUS_GENERATED,
    LOCKED_RISK_DISCLAIMER_NL,
    validate_explanation_output,
)

from portfolio_outlook_api.ai_explanation_provider import (
    ExplanationProviderInputs,
    ExplanationProviderProtocol,
    ExplanationProviderUnavailable,
)

logger = logging.getLogger(__name__)

AlertSummaryKind = Literal["digest", "morning_alerts"]


@dataclass(frozen=True)
class AlertSummaryResult:
    """Outcome of one composition attempt.

    ``summary_nl`` is populated only when ``status == "generated"`` —
    every blocked / failed / provider-unavailable path carries
    ``summary_nl=None`` so callers always fall through to the
    deterministic template body without branching on truthy strings.
    """

    status: str
    summary_nl: str | None
    blocking_reason: str | None
    hallucinated_numbers: tuple[str, ...]


def _build_canonical_input(
    *,
    kind: AlertSummaryKind,
    context_text: str,
    alert_lines: Sequence[str],
) -> str:
    joined_alerts = "\n".join(alert_lines).strip()
    return (
        f"[type] {kind}\n"
        f"[context]\n{context_text.strip()}\n\n"
        f"[alerts]\n{joined_alerts or '(geen)'}"
    )


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compose_alert_summary(
    *,
    kind: AlertSummaryKind,
    context_text: str,
    alert_lines: Sequence[str],
    provider: ExplanationProviderProtocol | ExplanationProviderUnavailable,
    max_output_chars: int,
) -> AlertSummaryResult:
    """Produce a Dutch summary header for an alert email.

    The caller has already composed the deterministic template body;
    the summary is meant to be *prepended* to that body, not to replace
    it. When the AI path fails for any reason, the caller sends the
    template-only email instead — no operational signal is lost.
    """

    if not alert_lines:
        # Nothing to summarise; the template already says "(geen)".
        return AlertSummaryResult(
            status="skipped_no_alerts",
            summary_nl=None,
            blocking_reason=None,
            hallucinated_numbers=(),
        )

    if isinstance(provider, ExplanationProviderUnavailable):
        return AlertSummaryResult(
            status="provider_unavailable",
            summary_nl=None,
            blocking_reason=provider.reason,
            hallucinated_numbers=(),
        )

    canonical_input = _build_canonical_input(
        kind=kind, context_text=context_text, alert_lines=alert_lines
    )
    # The provider's ``ExplanationProviderInputs`` is Decision-Package
    # shaped; we feed it the alert-shaped data via the generic Dutch
    # fields so the stub provider's paraphrase has something coherent
    # to echo. The real Anthropic provider reads ``input_text`` and
    # the system prompt does the heavy lifting.
    inputs = ExplanationProviderInputs(
        decision_package_id=f"alert_summary_{kind}",
        decision_package_content_hash=_hash_text(canonical_input)[:32],
        symbol=kind,
        risk_profile="",
        rationale_nl=context_text,
        package_explanation_nl="\n".join(alert_lines),
        research_snippet_nl=None,
        input_text=canonical_input,
    )

    try:
        provider_result = provider.generate(inputs)
    except Exception as exc:  # noqa: BLE001 — boundary catch
        logger.warning("alert summary provider failed: %s", exc)
        return AlertSummaryResult(
            status=EXPLANATION_STATUS_FAILED,
            summary_nl=None,
            blocking_reason="provider_error",
            hallucinated_numbers=(),
        )

    validation = validate_explanation_output(
        output_text=provider_result.output_text,
        input_evidence_text=canonical_input,
        max_output_chars=max_output_chars,
        disclaimer=LOCKED_RISK_DISCLAIMER_NL,
    )
    if validation.status != EXPLANATION_STATUS_GENERATED:
        return AlertSummaryResult(
            status=validation.status,
            summary_nl=None,
            blocking_reason=validation.blocking_reason,
            hallucinated_numbers=validation.hallucinated_numbers,
        )

    return AlertSummaryResult(
        status=EXPLANATION_STATUS_GENERATED,
        summary_nl=provider_result.output_text.strip(),
        blocking_reason=None,
        hallucinated_numbers=(),
    )


__all__ = [
    "AlertSummaryKind",
    "AlertSummaryResult",
    "compose_alert_summary",
]
