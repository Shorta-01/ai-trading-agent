from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from portfolio_outlook_api.ibkr_sync_contracts import (
    IbkrCash,
    IbkrExecution,
    IbkrOpenOrder,
    IbkrPosition,
)

_ALLOWED_SECURITY_TYPES = {"STK", "ETF"}
_ALLOWED_ORDER_SIDES = {"BUY", "SELL"}
_ALLOWED_EXECUTION_SIDES = {"BUY", "SELL", "BOT", "SLD"}


@dataclass(frozen=True)
class PayloadValidationError:
    payload_kind: str
    item_index: int | None
    field_name: str | None
    reason_code: str
    message_nl: str


@dataclass(frozen=True)
class PayloadValidationResult:
    passed: bool
    errors: list[PayloadValidationError]


def _is_currency(value: str) -> bool:
    return len(value) == 3 and value.isalpha() and value.isupper()


def _append(
    errors: list[PayloadValidationError],
    kind: str,
    idx: int | None,
    field: str | None,
    code: str,
    message: str,
) -> None:
    errors.append(PayloadValidationError(kind, idx, field, code, message))


def validate_ibkr_sync_payloads(
    cash_items: list[IbkrCash],
    positions: list[IbkrPosition],
    open_orders: list[IbkrOpenOrder],
    executions: list[IbkrExecution],
) -> PayloadValidationResult:
    errors: list[PayloadValidationError] = []

    for idx, cash_item in enumerate(cash_items):
        if not cash_item.account_ref:
            _append(errors, "cash", idx, "account_ref", "required", "Accountreferentie ontbreekt.")
        if not _is_currency(cash_item.base_currency):
            _append(
                errors,
                "cash",
                idx,
                "base_currency",
                "invalid_currency",
                "Basismunt moet 3 hoofdletters zijn.",
            )
        if not isinstance(cash_item.cash, Decimal):
            _append(errors, "cash", idx, "cash", "invalid_decimal", "Cash moet een Decimal zijn.")
        for field in ("available_funds", "buying_power"):
            value = getattr(cash_item, field)
            if value is not None and not isinstance(value, Decimal):
                _append(
                    errors, "cash", idx, field, "invalid_decimal", "Waarde moet een Decimal zijn."
                )

    seen_position_keys: set[tuple[str, str, str]] = set()
    for idx, position_item in enumerate(positions):
        if not position_item.account_ref:
            _append(
                errors, "position", idx, "account_ref", "required", "Accountreferentie ontbreekt."
            )
        if not position_item.symbol:
            _append(errors, "position", idx, "symbol", "required", "Symbool ontbreekt.")
        if position_item.security_type not in _ALLOWED_SECURITY_TYPES:
            _append(
                errors,
                "position",
                idx,
                "security_type",
                "unsupported_security_type",
                "Niet-ondersteund effecttype voor Version 1.",
            )
        if not _is_currency(position_item.currency):
            _append(
                errors,
                "position",
                idx,
                "currency",
                "invalid_currency",
                "Munt moet 3 hoofdletters zijn.",
            )
        if not isinstance(position_item.quantity, Decimal) or position_item.quantity < Decimal("0"):
            _append(
                errors,
                "position",
                idx,
                "quantity",
                "invalid_quantity",
                "Aantal moet Decimal en niet-negatief zijn.",
            )
        if position_item.average_cost is not None and (
            not isinstance(position_item.average_cost, Decimal)
            or position_item.average_cost < Decimal("0")
        ):
            _append(
                errors,
                "position",
                idx,
                "average_cost",
                "invalid_decimal",
                "Gemiddelde kost moet Decimal en niet-negatief zijn.",
            )
        if position_item.conid is not None and position_item.conid <= 0:
            _append(errors, "position", idx, "conid", "invalid_id", "conid moet positief zijn.")
        key = (position_item.account_ref, position_item.symbol, position_item.security_type)
        if key in seen_position_keys:
            _append(
                errors,
                "position",
                idx,
                "identity",
                "duplicate_identity",
                "Dubbele positie-identiteit in payload.",
            )
        seen_position_keys.add(key)

    seen_order_ids: set[int] = set()
    for idx, open_order_item in enumerate(open_orders):
        if not open_order_item.account_ref:
            _append(
                errors, "open_order", idx, "account_ref", "required", "Accountreferentie ontbreekt."
            )
        if open_order_item.ibkr_order_id <= 0:
            _append(
                errors,
                "open_order",
                idx,
                "ibkr_order_id",
                "invalid_id",
                "Order-ID moet positief zijn.",
            )
        if not open_order_item.symbol:
            _append(errors, "open_order", idx, "symbol", "required", "Symbool ontbreekt.")
        if open_order_item.security_type not in _ALLOWED_SECURITY_TYPES:
            _append(
                errors,
                "open_order",
                idx,
                "security_type",
                "unsupported_security_type",
                "Niet-ondersteund effecttype voor Version 1.",
            )
        if not _is_currency(open_order_item.currency):
            _append(
                errors,
                "open_order",
                idx,
                "currency",
                "invalid_currency",
                "Munt moet 3 hoofdletters zijn.",
            )
        if open_order_item.action_side not in _ALLOWED_ORDER_SIDES:
            _append(
                errors,
                "open_order",
                idx,
                "action_side",
                "invalid_side",
                "Orderrichting moet BUY of SELL zijn.",
            )
        if not open_order_item.order_type:
            _append(errors, "open_order", idx, "order_type", "required", "Ordertype ontbreekt.")
        if not isinstance(open_order_item.quantity, Decimal) or open_order_item.quantity <= 0:
            _append(
                errors,
                "open_order",
                idx,
                "quantity",
                "invalid_quantity",
                "Aantal moet Decimal en positief zijn.",
            )
        if (
            not isinstance(open_order_item.filled_quantity, Decimal)
            or open_order_item.filled_quantity < 0
        ):
            _append(
                errors,
                "open_order",
                idx,
                "filled_quantity",
                "invalid_quantity",
                "Filled quantity moet Decimal en niet-negatief zijn.",
            )
        if (
            not isinstance(open_order_item.remaining_quantity, Decimal)
            or open_order_item.remaining_quantity < 0
        ):
            _append(
                errors,
                "open_order",
                idx,
                "remaining_quantity",
                "invalid_quantity",
                "Remaining quantity moet Decimal en niet-negatief zijn.",
            )
        for field in ("limit_price", "stop_price"):
            value = getattr(open_order_item, field)
            if value is not None and (not isinstance(value, Decimal) or value <= 0):
                _append(
                    errors,
                    "open_order",
                    idx,
                    field,
                    "invalid_decimal",
                    "Prijs moet Decimal en positief zijn.",
                )
        if not open_order_item.status:
            _append(errors, "open_order", idx, "status", "required", "Orderstatus ontbreekt.")
        if open_order_item.ibkr_order_id in seen_order_ids:
            _append(
                errors,
                "open_order",
                idx,
                "ibkr_order_id",
                "duplicate_order_id",
                "Dubbele open-order ID in payload.",
            )
        seen_order_ids.add(open_order_item.ibkr_order_id)

    seen_execution_ids: set[str] = set()
    for idx, execution_item in enumerate(executions):
        if not execution_item.account_ref:
            _append(
                errors, "execution", idx, "account_ref", "required", "Accountreferentie ontbreekt."
            )
        if not execution_item.execution_id:
            _append(errors, "execution", idx, "execution_id", "required", "Execution-ID ontbreekt.")
        if execution_item.ibkr_order_id <= 0:
            _append(
                errors,
                "execution",
                idx,
                "ibkr_order_id",
                "invalid_id",
                "Order-ID moet positief zijn.",
            )
        if not execution_item.symbol:
            _append(errors, "execution", idx, "symbol", "required", "Symbool ontbreekt.")
        if execution_item.security_type not in _ALLOWED_SECURITY_TYPES:
            _append(
                errors,
                "execution",
                idx,
                "security_type",
                "unsupported_security_type",
                "Niet-ondersteund effecttype voor Version 1.",
            )
        if not _is_currency(execution_item.currency):
            _append(
                errors,
                "execution",
                idx,
                "currency",
                "invalid_currency",
                "Munt moet 3 hoofdletters zijn.",
            )
        if execution_item.side not in _ALLOWED_EXECUTION_SIDES:
            _append(errors, "execution", idx, "side", "invalid_side", "Execution-kant is ongeldig.")
        if not isinstance(execution_item.quantity, Decimal) or execution_item.quantity <= 0:
            _append(
                errors,
                "execution",
                idx,
                "quantity",
                "invalid_quantity",
                "Aantal moet Decimal en positief zijn.",
            )
        if not isinstance(execution_item.price, Decimal) or execution_item.price <= 0:
            _append(
                errors,
                "execution",
                idx,
                "price",
                "invalid_decimal",
                "Prijs moet Decimal en positief zijn.",
            )
        if not isinstance(execution_item.execution_time, datetime):
            _append(
                errors,
                "execution",
                idx,
                "execution_time",
                "invalid_datetime",
                "Execution-tijd moet datetime zijn.",
            )
        for field in ("commission", "realized_pnl"):
            value = getattr(execution_item, field)
            if value is not None and not isinstance(value, Decimal):
                _append(
                    errors, "execution", idx, field, "invalid_decimal", "Waarde moet Decimal zijn."
                )
        if execution_item.execution_id in seen_execution_ids:
            _append(
                errors,
                "execution",
                idx,
                "execution_id",
                "duplicate_execution_id",
                "Dubbele execution-ID in payload.",
            )
        seen_execution_ids.add(execution_item.execution_id)

    return PayloadValidationResult(passed=len(errors) == 0, errors=errors)
