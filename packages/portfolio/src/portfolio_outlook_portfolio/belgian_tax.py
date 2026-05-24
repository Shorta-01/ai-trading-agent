"""Belgian tax helpers (Slice 11) — TOB + dividend roerende voorheffing.

The Belgian *Beurstaks* (TOB / Taxe sur les Opérations de Bourse) is a
fixed-rate transaction tax. The rate depends on the security class and
the tax is capped per transaction. Locked rates and caps (as of 2025):

* 0.12% — bonds, ``BOND``                                — cap €1 300
* 0.35% — listed shares + distributing ETFs              — cap €1 600
* 1.32% — accumulating ETFs / SICAV redemptions          — cap €4 000

Belgian residents owe a 30% *roerende voorheffing* on dividend income;
that's captured by :func:`compute_dividend_withholding`.

All math is Decimal-only. This module is **pure Python**: no I/O, no
config dependencies, no datetime.now(). Both functions return the
amount of tax owed (always positive, capped per the table above).

This is *informational* in V1 — it surfaces on the Decision Package
Orderimpact and the Action-draft preview, but the doctrine still keeps
``safe_for_*`` flags hard-False on every persisted row. The TOB does
not change order sizing.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum


class TobSecurityClass(StrEnum):
    """Locked Belgian TOB security classes.

    The string values are stored on the action-draft row so the audit
    chain can prove which rate was applied.
    """

    STANDARD_STOCK = "standard_stock"  # listed equity → 0.35%
    DISTRIBUTING_ETF = "distributing_etf"  # distributing fund/ETF → 0.35%
    ACCUMULATING_ETF = "accumulating_etf"  # accumulating fund/ETF → 1.32%
    BOND = "bond"  # listed bond → 0.12%
    SICAV_REDEMPTION = "sicav_redemption"  # SICAV redemption → 1.32%
    OTHER = "other"  # conservative default → 0.35%


@dataclass(frozen=True)
class TobRateInfo:
    rate: Decimal
    cap: Decimal


# Locked rates + per-transaction caps (EUR, 2025 schedule).
TOB_RATE_BOND = Decimal("0.0012")
TOB_RATE_STANDARD = Decimal("0.0035")
TOB_RATE_ACCUMULATING = Decimal("0.0132")

TOB_CAP_BOND = Decimal("1300")
TOB_CAP_STANDARD = Decimal("1600")
TOB_CAP_ACCUMULATING = Decimal("4000")

BELGIAN_DIVIDEND_WITHHOLDING_RATE = Decimal("0.30")

_RATE_TABLE: dict[TobSecurityClass, TobRateInfo] = {
    TobSecurityClass.STANDARD_STOCK: TobRateInfo(TOB_RATE_STANDARD, TOB_CAP_STANDARD),
    TobSecurityClass.DISTRIBUTING_ETF: TobRateInfo(TOB_RATE_STANDARD, TOB_CAP_STANDARD),
    TobSecurityClass.ACCUMULATING_ETF: TobRateInfo(
        TOB_RATE_ACCUMULATING, TOB_CAP_ACCUMULATING
    ),
    TobSecurityClass.BOND: TobRateInfo(TOB_RATE_BOND, TOB_CAP_BOND),
    TobSecurityClass.SICAV_REDEMPTION: TobRateInfo(
        TOB_RATE_ACCUMULATING, TOB_CAP_ACCUMULATING
    ),
    TobSecurityClass.OTHER: TobRateInfo(TOB_RATE_STANDARD, TOB_CAP_STANDARD),
}

_TWO_DECIMALS = Decimal("0.01")


def _round_eur_cents(value: Decimal) -> Decimal:
    """Round to euro cents with HALF_UP (the convention IBKR + brokers use)."""

    return value.quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)


def tob_rate_info(security_class: TobSecurityClass) -> TobRateInfo:
    """Return ``(rate, cap)`` for ``security_class``. Useful for tests + UI."""

    return _RATE_TABLE[security_class]


def compute_tob(
    *,
    transaction_value: Decimal,
    security_class: TobSecurityClass,
) -> Decimal:
    """Return the TOB amount (EUR cents) owed on one transaction.

    ``transaction_value`` is the gross transaction value in EUR (price ×
    quantity, pre-tax). The result is the smaller of
    ``transaction_value * rate`` and the per-transaction cap, rounded
    HALF_UP to cents.

    A ``transaction_value`` of zero returns ``Decimal("0")``. Negative
    values raise ``ValueError`` — the caller should normalise the side
    before computing the tax.
    """

    if not isinstance(transaction_value, Decimal):
        raise TypeError("transaction_value must be a Decimal")
    if transaction_value < 0:
        raise ValueError("transaction_value must not be negative")
    if transaction_value == 0:
        return Decimal("0.00")
    info = _RATE_TABLE[security_class]
    raw = transaction_value * info.rate
    return _round_eur_cents(min(raw, info.cap))


def compute_dividend_withholding(*, gross_dividend: Decimal) -> Decimal:
    """Return the Belgian roerende voorheffing on a gross dividend payment.

    Rate is locked at 30%. A ``gross_dividend`` of zero returns
    ``Decimal("0")``. Negative values raise ``ValueError``.
    """

    if not isinstance(gross_dividend, Decimal):
        raise TypeError("gross_dividend must be a Decimal")
    if gross_dividend < 0:
        raise ValueError("gross_dividend must not be negative")
    if gross_dividend == 0:
        return Decimal("0.00")
    return _round_eur_cents(gross_dividend * BELGIAN_DIVIDEND_WITHHOLDING_RATE)


__all__ = [
    "TobSecurityClass",
    "TobRateInfo",
    "TOB_RATE_BOND",
    "TOB_RATE_STANDARD",
    "TOB_RATE_ACCUMULATING",
    "TOB_CAP_BOND",
    "TOB_CAP_STANDARD",
    "TOB_CAP_ACCUMULATING",
    "BELGIAN_DIVIDEND_WITHHOLDING_RATE",
    "tob_rate_info",
    "compute_tob",
    "compute_dividend_withholding",
]
