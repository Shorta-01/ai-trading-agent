from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class IbkrAccountCashPreflightItem:
    tag: str
    currency: str | None
    value: Decimal | str
    source: str
    parse_status: str


@dataclass(frozen=True)
class IbkrPositionPreflightItem:
    account_mode: str
    masked_account_id: str | None
    symbol: str | None
    sec_type: str | None
    currency: str | None
    exchange: str | None
    primary_exchange: str | None
    con_id: int | None
    quantity: Decimal
    average_cost: Decimal | None
    source: str


def mask_account_id(account_id: str) -> str:
    cleaned = account_id.strip()
    if len(cleaned) <= 3:
        return "***"
    return f"{cleaned[:2]}****{cleaned[-3:]}"


def parse_decimal_or_text(value: str) -> tuple[Decimal | str, str]:
    try:
        return Decimal(value), "parsed"
    except (InvalidOperation, ValueError):
        return value.strip(), "unparsed"
