"""Tests for the Belgian tax helpers (Slice 11)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    BELGIAN_DIVIDEND_WITHHOLDING_RATE,
    TOB_CAP_ACCUMULATING,
    TOB_CAP_BOND,
    TOB_CAP_STANDARD,
    TOB_RATE_ACCUMULATING,
    TOB_RATE_BOND,
    TOB_RATE_STANDARD,
    TobSecurityClass,
    compute_dividend_withholding,
    compute_tob,
    tob_rate_info,
)

# ---- TOB ---------------------------------------------------------------


def test_standard_stock_uses_0_35_pct_rate() -> None:
    tax = compute_tob(
        transaction_value=Decimal("1000"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert tax == Decimal("3.50")


def test_distributing_etf_uses_0_35_pct_rate() -> None:
    tax = compute_tob(
        transaction_value=Decimal("1000"),
        security_class=TobSecurityClass.DISTRIBUTING_ETF,
    )
    assert tax == Decimal("3.50")


def test_bond_uses_0_12_pct_rate() -> None:
    tax = compute_tob(
        transaction_value=Decimal("10000"),
        security_class=TobSecurityClass.BOND,
    )
    assert tax == Decimal("12.00")


def test_accumulating_etf_uses_1_32_pct_rate() -> None:
    tax = compute_tob(
        transaction_value=Decimal("1000"),
        security_class=TobSecurityClass.ACCUMULATING_ETF,
    )
    assert tax == Decimal("13.20")


def test_sicav_redemption_uses_high_rate() -> None:
    tax = compute_tob(
        transaction_value=Decimal("1000"),
        security_class=TobSecurityClass.SICAV_REDEMPTION,
    )
    assert tax == Decimal("13.20")


def test_other_security_class_falls_back_to_standard_rate() -> None:
    tax = compute_tob(
        transaction_value=Decimal("1000"),
        security_class=TobSecurityClass.OTHER,
    )
    assert tax == Decimal("3.50")


def test_zero_transaction_value_returns_zero() -> None:
    tax = compute_tob(
        transaction_value=Decimal("0"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert tax == Decimal("0.00")


def test_negative_transaction_value_raises() -> None:
    with pytest.raises(ValueError, match="not be negative"):
        compute_tob(
            transaction_value=Decimal("-100"),
            security_class=TobSecurityClass.STANDARD_STOCK,
        )


def test_non_decimal_transaction_value_raises() -> None:
    with pytest.raises(TypeError, match="must be a Decimal"):
        compute_tob(
            transaction_value=1000,  # type: ignore[arg-type]
            security_class=TobSecurityClass.STANDARD_STOCK,
        )


def test_tob_is_capped_for_standard_rate() -> None:
    # 1,000,000 * 0.35% = 3,500 but the cap is 1,600.
    tax = compute_tob(
        transaction_value=Decimal("1000000"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert tax == TOB_CAP_STANDARD


def test_tob_is_capped_for_bond_rate() -> None:
    # 10,000,000 * 0.12% = 12,000 but the cap is 1,300.
    tax = compute_tob(
        transaction_value=Decimal("10000000"),
        security_class=TobSecurityClass.BOND,
    )
    assert tax == TOB_CAP_BOND


def test_tob_is_capped_for_accumulating_rate() -> None:
    # 1,000,000 * 1.32% = 13,200 but the cap is 4,000.
    tax = compute_tob(
        transaction_value=Decimal("1000000"),
        security_class=TobSecurityClass.ACCUMULATING_ETF,
    )
    assert tax == TOB_CAP_ACCUMULATING


def test_tob_rounds_half_up_to_cents() -> None:
    # 999.99 * 0.35% = 3.499965 → 3.50
    tax = compute_tob(
        transaction_value=Decimal("999.99"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert tax == Decimal("3.50")
    # 142.86 * 0.35% = 0.500010 → 0.50
    tax = compute_tob(
        transaction_value=Decimal("142.86"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert tax == Decimal("0.50")


def test_tob_rate_info_exposes_rate_and_cap_per_class() -> None:
    info = tob_rate_info(TobSecurityClass.STANDARD_STOCK)
    assert info.rate == TOB_RATE_STANDARD
    assert info.cap == TOB_CAP_STANDARD

    info = tob_rate_info(TobSecurityClass.BOND)
    assert info.rate == TOB_RATE_BOND

    info = tob_rate_info(TobSecurityClass.ACCUMULATING_ETF)
    assert info.rate == TOB_RATE_ACCUMULATING


# ---- Dividend withholding ---------------------------------------------


def test_dividend_withholding_is_30_percent() -> None:
    tax = compute_dividend_withholding(gross_dividend=Decimal("100"))
    assert tax == Decimal("30.00")
    assert BELGIAN_DIVIDEND_WITHHOLDING_RATE == Decimal("0.30")


def test_dividend_withholding_zero_returns_zero() -> None:
    assert compute_dividend_withholding(gross_dividend=Decimal("0")) == Decimal("0.00")


def test_dividend_withholding_negative_raises() -> None:
    with pytest.raises(ValueError, match="not be negative"):
        compute_dividend_withholding(gross_dividend=Decimal("-100"))


def test_dividend_withholding_non_decimal_raises() -> None:
    with pytest.raises(TypeError, match="must be a Decimal"):
        compute_dividend_withholding(gross_dividend=100)  # type: ignore[arg-type]


def test_dividend_withholding_rounds_half_up() -> None:
    # 33.335 * 0.30 = 10.0005 → 10.00
    tax = compute_dividend_withholding(gross_dividend=Decimal("33.335"))
    assert tax == Decimal("10.00")
    # 33.34 * 0.30 = 10.002 → 10.00
    tax = compute_dividend_withholding(gross_dividend=Decimal("33.34"))
    assert tax == Decimal("10.00")
    # 16.685 * 0.30 = 5.0055 → 5.01
    tax = compute_dividend_withholding(gross_dividend=Decimal("16.685"))
    assert tax == Decimal("5.01")
