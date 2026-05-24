"""Tests for the deterministic AI explanation guards (Slice 10)."""

from __future__ import annotations

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_DISCLAIMER_MISSING,
    BLOCKING_REASON_EMPTY_OUTPUT,
    BLOCKING_REASON_HALLUCINATED_NUMBERS,
    BLOCKING_REASON_OUTPUT_TOO_LONG,
    EXPLANATION_STATUS_BLOCKED,
    EXPLANATION_STATUS_GENERATED,
    LOCKED_RISK_DISCLAIMER_NL,
    validate_explanation_output,
)


def test_output_with_all_numbers_in_input_and_disclaimer_is_generated() -> None:
    input_text = (
        "Symbol AAPL, prijs 180, p10 170, p50 182, p90 194, kans op stijging 0.62, "
        "horizon 21 dagen."
    )
    output_text = (
        "AAPL noteert nu 180. De voorspelde mediane prijs over 21 dagen is 182, "
        "met p10 170 en p90 194 en een kans op stijging van 0.62. "
        f"{LOCKED_RISK_DISCLAIMER_NL}"
    )
    result = validate_explanation_output(
        output_text=output_text,
        input_evidence_text=input_text,
        max_output_chars=1000,
    )
    assert result.status == EXPLANATION_STATUS_GENERATED
    assert result.blocking_reason is None
    assert result.hallucinated_numbers == ()


def test_hallucinated_number_blocks_output() -> None:
    input_text = "p50 182"
    output_text = (
        "De voorspelde prijs is 200. " + LOCKED_RISK_DISCLAIMER_NL
    )
    result = validate_explanation_output(
        output_text=output_text,
        input_evidence_text=input_text,
        max_output_chars=1000,
    )
    assert result.status == EXPLANATION_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_HALLUCINATED_NUMBERS
    assert "200" in result.hallucinated_numbers


def test_missing_disclaimer_blocks_output() -> None:
    input_text = "prijs 180"
    output_text = "AAPL noteert nu 180 zonder disclaimer."
    result = validate_explanation_output(
        output_text=output_text,
        input_evidence_text=input_text,
        max_output_chars=1000,
    )
    assert result.status == EXPLANATION_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_DISCLAIMER_MISSING


def test_empty_output_is_blocked() -> None:
    result = validate_explanation_output(
        output_text="   \n  ",
        input_evidence_text="prijs 180",
        max_output_chars=1000,
    )
    assert result.status == EXPLANATION_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_EMPTY_OUTPUT


def test_output_exceeding_max_length_is_blocked() -> None:
    input_text = "prijs 180"
    long_output = (
        "Lange tekst " * 200 + " 180 " + LOCKED_RISK_DISCLAIMER_NL
    )
    result = validate_explanation_output(
        output_text=long_output,
        input_evidence_text=input_text,
        max_output_chars=200,
    )
    assert result.status == EXPLANATION_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_OUTPUT_TOO_LONG


def test_decimal_formatting_variations_match_input() -> None:
    """`180` in input matches `180.00` in output and vice versa."""

    input_text = "prijs 180.00, p50 182.50"
    output_text = (
        "AAPL noteert nu 180. De mediane prijs is 182.5. "
        + LOCKED_RISK_DISCLAIMER_NL
    )
    result = validate_explanation_output(
        output_text=output_text,
        input_evidence_text=input_text,
        max_output_chars=1000,
    )
    assert result.status == EXPLANATION_STATUS_GENERATED


def test_dutch_decimal_comma_matches_dot_in_input() -> None:
    """Output written with a Dutch decimal comma matches input with a dot."""

    input_text = "p50 182.5, prob_gain 0.62"
    output_text = (
        "De mediane prijs is 182,5 met een kans van 0,62. "
        + LOCKED_RISK_DISCLAIMER_NL
    )
    result = validate_explanation_output(
        output_text=output_text,
        input_evidence_text=input_text,
        max_output_chars=1000,
    )
    assert result.status == EXPLANATION_STATUS_GENERATED


def test_percent_suffix_is_stripped_for_matching() -> None:
    input_text = "expected_return_pct 5.0"
    output_text = (
        "Het verwacht rendement is 5.0%. " + LOCKED_RISK_DISCLAIMER_NL
    )
    result = validate_explanation_output(
        output_text=output_text,
        input_evidence_text=input_text,
        max_output_chars=1000,
    )
    assert result.status == EXPLANATION_STATUS_GENERATED


def test_thousand_separator_normalisation() -> None:
    """`1,000` and `1000` and `1.000` are treated as the same number."""

    input_text = "cash 1,000"
    output_text = "Cash beschikbaar: 1000 USD. " + LOCKED_RISK_DISCLAIMER_NL
    result = validate_explanation_output(
        output_text=output_text,
        input_evidence_text=input_text,
        max_output_chars=1000,
    )
    assert result.status == EXPLANATION_STATUS_GENERATED


def test_multiple_hallucinations_are_all_reported() -> None:
    input_text = "prijs 180"
    output_text = (
        "Doelprijs 250, stop-loss 165, target 300. " + LOCKED_RISK_DISCLAIMER_NL
    )
    result = validate_explanation_output(
        output_text=output_text,
        input_evidence_text=input_text,
        max_output_chars=1000,
    )
    assert result.status == EXPLANATION_STATUS_BLOCKED
    assert set(result.hallucinated_numbers) == {"165", "250", "300"}
