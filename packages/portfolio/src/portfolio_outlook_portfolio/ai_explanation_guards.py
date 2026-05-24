"""Deterministic guards around the AI explanation layer (Slice 10).

The locked V1 doctrine
(release-1-functional-workflow-blueprint.md §6 + §8):

* AI **never** originates a financial number. An explanation can only
  paraphrase the persisted Decision Package + linked research evidence.
* Every explanation is bound to a specific
  ``(decision_package_id, decision_package_content_hash)`` pair, so a
  new package version always needs a new explanation.
* Output must include a Dutch risk disclaimer.
* Every numeric token in the AI output must also appear in the input
  evidence set. If a number is missing from the input, the output is
  **blocked** — not displayed as a suggestion. This is the hallucination
  guard.

This module is pure Python — no I/O, no datetime.now(), no dependency
on the AI provider. The orchestrator wires it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

LOCKED_RISK_DISCLAIMER_NL = (
    "Deze uitleg is een samenvatting van bewijs uit de Decision Package "
    "en gekoppelde bronnen. Het is geen advies; AI bedenkt nooit nieuwe "
    "getallen. Controleer de evidence-bundel en de bronnen zelf voordat "
    "je een beslissing neemt."
)

EXPLANATION_STATUS_GENERATED = "generated"
EXPLANATION_STATUS_BLOCKED = "blocked"
EXPLANATION_STATUS_FAILED = "failed"

BLOCKING_REASON_HALLUCINATED_NUMBERS = "hallucinated_numbers"
BLOCKING_REASON_DISCLAIMER_MISSING = "disclaimer_missing"
BLOCKING_REASON_EMPTY_OUTPUT = "empty_output"
BLOCKING_REASON_OUTPUT_TOO_LONG = "output_too_long"

# Regex that captures any numeric token in a text:
# - integer or decimal
# - optional leading minus
# - optional thousand separators (commas or dots, but we normalise away)
# - optional percent suffix is stripped before comparison
# We extract the "raw" numeric token; normalisation handles formatting
# differences in :func:`_normalise_numeric_token`.
_NUMERIC_TOKEN_PATTERN = re.compile(
    # First alternative: thousand-separated form like 1,000 or 1.234.567 — the
    # `+` ensures at least one separator group, so plain integers fall through
    # to the second alternative instead of being clipped.
    r"-?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|-?\d+(?:[.,]\d+)?"
)


@dataclass(frozen=True)
class ExplanationValidationResult:
    status: str
    blocking_reason: str | None
    hallucinated_numbers: tuple[str, ...]


def _normalise_numeric_token(token: str) -> str:
    """Map a numeric string into a stable canonical form.

    Strategy: strip whitespace and any trailing ``%``; remove all
    thousand-separator dots/commas; collapse the remaining ``,`` (used
    as decimal separator in Dutch text) to ``.``. The result is a plain
    decimal string. We then trim trailing zeros after a decimal point
    so ``180`` and ``180.0`` and ``180.00`` are considered the same.
    """

    cleaned = token.strip().rstrip("%").strip()
    # First, remove thousand separators. We treat a dot/comma followed
    # by exactly three digits at a non-final position as a thousand
    # separator and any other dot/comma as a decimal separator.
    # The locale-agnostic approach: count separators; if a token has
    # both ``.`` and ``,`` we keep the rightmost as decimal and treat
    # the other as thousands.
    if "." in cleaned and "," in cleaned:
        if cleaned.rfind(".") > cleaned.rfind(","):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        # Only one type of separator. Decide whether it's a decimal
        # separator or a thousand separator by checking the length of
        # the segment after the last separator.
        for separator in (",", "."):
            if separator in cleaned:
                tail = cleaned.rsplit(separator, 1)[1]
                if len(tail) == 3 and tail.isdigit():
                    # Treat as thousand separator → drop all occurrences
                    cleaned = cleaned.replace(separator, "")
                elif separator == ",":
                    cleaned = cleaned.replace(",", ".")
                break
    # Trim trailing zeros for decimal forms.
    if "." in cleaned:
        cleaned = cleaned.rstrip("0").rstrip(".") or "0"
    return cleaned


def _extract_numeric_tokens(text: str) -> set[str]:
    return {
        _normalise_numeric_token(match.group())
        for match in _NUMERIC_TOKEN_PATTERN.finditer(text)
    }


def validate_explanation_output(
    *,
    output_text: str,
    input_evidence_text: str,
    max_output_chars: int,
    disclaimer: str = LOCKED_RISK_DISCLAIMER_NL,
) -> ExplanationValidationResult:
    """Apply the V1 doctrine to one AI output.

    Returns the final ``status`` (``generated`` / ``blocked``) and the
    list of hallucinated numbers (empty when status is ``generated``).
    The disclaimer-missing and output-too-long checks block before the
    numeric check so the failure reason is the cheapest-to-explain one.
    """

    stripped = output_text.strip()
    if not stripped:
        return ExplanationValidationResult(
            status=EXPLANATION_STATUS_BLOCKED,
            blocking_reason=BLOCKING_REASON_EMPTY_OUTPUT,
            hallucinated_numbers=(),
        )
    if len(stripped) > max_output_chars:
        return ExplanationValidationResult(
            status=EXPLANATION_STATUS_BLOCKED,
            blocking_reason=BLOCKING_REASON_OUTPUT_TOO_LONG,
            hallucinated_numbers=(),
        )
    if disclaimer not in stripped:
        return ExplanationValidationResult(
            status=EXPLANATION_STATUS_BLOCKED,
            blocking_reason=BLOCKING_REASON_DISCLAIMER_MISSING,
            hallucinated_numbers=(),
        )
    input_numbers = _extract_numeric_tokens(input_evidence_text)
    output_numbers = _extract_numeric_tokens(stripped)
    hallucinated = sorted(output_numbers - input_numbers)
    if hallucinated:
        return ExplanationValidationResult(
            status=EXPLANATION_STATUS_BLOCKED,
            blocking_reason=BLOCKING_REASON_HALLUCINATED_NUMBERS,
            hallucinated_numbers=tuple(hallucinated),
        )
    return ExplanationValidationResult(
        status=EXPLANATION_STATUS_GENERATED,
        blocking_reason=None,
        hallucinated_numbers=(),
    )


__all__ = [
    "LOCKED_RISK_DISCLAIMER_NL",
    "EXPLANATION_STATUS_GENERATED",
    "EXPLANATION_STATUS_BLOCKED",
    "EXPLANATION_STATUS_FAILED",
    "BLOCKING_REASON_HALLUCINATED_NUMBERS",
    "BLOCKING_REASON_DISCLAIMER_MISSING",
    "BLOCKING_REASON_EMPTY_OUTPUT",
    "BLOCKING_REASON_OUTPUT_TOO_LONG",
    "ExplanationValidationResult",
    "validate_explanation_output",
]
