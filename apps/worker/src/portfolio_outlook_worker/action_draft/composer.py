"""Task 133: pure Action Draft composition.

The composer is the **only** code path that mints an
``ActionDraftEntry``. It is a pure function — every output field is
deterministically derived from the inputs. No AI. No network calls.

Doctrine bindings (Task 133 product locks §3 + §4 + §5):

* **AI never originates an Action Draft field.** Side is copied from
  the Decision Package's suggested_action_label; quantity is computed
  from the cash-aware sizing rules; limit price is derived from
  current_price_local ± 2 basis points; everything else is a snapshot.
* **Decimal end-to-end.** No ``float`` anywhere in the composition path,
  including inside the hash input.
* **Immutable.** ``ActionDraftEntry`` is frozen; the composer never
  mutates input records.
* **Cash-aware sizing** (Task 133 product lock §4): BUY drafts inspect
  ``usable_cash_eur_at_creation = available_funds - approved_drafts -
  user_buffer_eur`` (pending IBKR-side orders are out of scope until
  Task 134); SELL drafts size from the held position only.
* **Hard-False safety boolean.** ``safe_for_submission`` is always
  False at composition time; Task 134 (real submission) is the only
  code path allowed to flip it conditionally.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
from uuid import uuid4

from ai_trading_agent_storage import (
    ActionDraftEntry,
    DecisionPackageEntry,
    FxRateRecord,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
)

# 2 basis points = 0.002 — the bias toward better fills (Task 133 lock §5).
_LIMIT_PRICE_BIAS_BPS = Decimal("0.002")
_QUANTITY_QUANTUM = Decimal("1")  # whole shares only for V1
_PRICE_QUANTUM = Decimal("0.00000001")  # 8 decimal places — matches DB
_NOTIONAL_QUANTUM = Decimal("0.00000001")

# Locked target percentages by (confidence, label) per the brainstorm
# Question 3 cash-aware sizing rules.
_BUY_TARGET_PCT_BY_CONFIDENCE: dict[str, Decimal] = {
    "Hoog": Decimal("0.08"),
    "Gemiddeld": Decimal("0.04"),
    # Laag is filtered by the Decision Package gates (Task 132 lock §5):
    # confidence_at_least_medium must pass before a package is composed.
    # We still defend here in case a downstream caller bypasses gates.
}
_SELL_VERMINDEREN_FRACTION = Decimal("0.25")


class InsufficientCashError(ValueError):
    """Raised when a BUY draft can't fund even one share.

    Carries ``max_affordable_quantity=Decimal("0")`` so the caller can
    surface the Dutch warning *"Onvoldoende cash voor positie op deze
    schaal. Verlaag het aantal of dismiss."* (Task 133 lock §4). When
    partial cash is available, the composer returns the draft with the
    max affordable quantity instead of raising — see
    ``compose_action_draft_from_decision_package``.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class NoPositionToSellError(ValueError):
    """Raised when a SELL draft is composed but no position exists."""


class UnsupportedDecisionPackageLabelError(ValueError):
    """Raised when the package's label can't be turned into a draft.

    Only Kopen / Verminderen / Verkopen produce action drafts.
    Houden / Bekijken don't — the user wouldn't action them — and
    Geblokkeerd is filtered upstream at the Decision Package layer.
    """


_DRAFTABLE_LABELS = frozenset({"Kopen", "Verminderen", "Verkopen"})


def compose_action_draft_from_decision_package(
    *,
    decision_package: DecisionPackageEntry,
    ibkr_cash_snapshot: IbkrAccountCashSnapshotRecord,
    ibkr_position_snapshot: IbkrPositionSnapshotRecord | None,
    fx_rate: FxRateRecord | None,
    user_buffer_eur: Decimal,
    portfolio_total_eur: Decimal | None = None,
    approved_drafts_notional_eur: Decimal = Decimal("0"),
    user_note: str | None = None,
    previous_draft_hash: str | None = None,
    created_at: datetime | None = None,
) -> ActionDraftEntry:
    """Compose an Action Draft from a Decision Package + IBKR context.

    Pure function — same inputs → same output (modulo ``created_at``
    and the generated ``action_draft_id``).

    Inputs:

    * ``decision_package`` — the source of truth for side / asset
      identity / confidence. Label must be in {Kopen, Verminderen,
      Verkopen}; Houden / Bekijken raise
      :class:`UnsupportedDecisionPackageLabelError`.
    * ``ibkr_cash_snapshot`` — the latest cash snapshot for the account.
      ``available_funds`` and ``base_currency`` must be set.
    * ``ibkr_position_snapshot`` — most-recent position for (account,
      conid). ``None`` means no position; required for SELL drafts.
    * ``fx_rate`` — local-to-EUR rate (``rate`` = EUR per 1 local unit).
      ``None`` only when the asset is EUR-denominated.
    * ``user_buffer_eur`` — headroom to subtract from available_funds
      before sizing. Default is €0 per Task 133 settings; user can
      change in Instellingen.
    * ``portfolio_total_eur`` — denominator for the percentage cap.
      ``None`` falls back to ``available_funds_eur`` (cash-only proxy).
    * ``approved_drafts_notional_eur`` — sum of approved-but-not-yet-
      submitted draft notionals for this account, subtracted from
      usable cash so the user can't over-commit.

    Raises:

    * :class:`UnsupportedDecisionPackageLabelError` for non-actionable
      labels.
    * :class:`NoPositionToSellError` for SELL with no position.
    * :class:`InsufficientCashError` if BUY can't fund 1 share even at
      zero buffer.
    """

    label = decision_package.suggested_action_label
    if label not in _DRAFTABLE_LABELS:
        raise UnsupportedDecisionPackageLabelError(
            f"Decision Package label {label!r} is not actionable "
            "(only Kopen / Verminderen / Verkopen produce drafts)."
        )

    side: str = "BUY" if label == "Kopen" else "SELL"
    limit_price_local = _compute_limit_price(
        current_price_local=decision_package.current_price_local, side=side
    )

    fx_rate_decimal = _resolve_fx_rate(
        currency_local=decision_package.currency_local, fx_rate=fx_rate
    )

    if ibkr_cash_snapshot.available_funds is None:
        raise ValueError(
            "ibkr_cash_snapshot.available_funds is required for "
            "Action Draft composition."
        )
    available_funds_eur = ibkr_cash_snapshot.available_funds
    if available_funds_eur < 0:
        available_funds_eur = Decimal("0")

    usable_cash_eur = (
        available_funds_eur
        - approved_drafts_notional_eur
        - user_buffer_eur
    )
    if usable_cash_eur < 0:
        usable_cash_eur = Decimal("0")

    portfolio_total_for_cap = (
        portfolio_total_eur
        if portfolio_total_eur is not None
        else available_funds_eur
    )

    held_quantity = (
        ibkr_position_snapshot.quantity
        if ibkr_position_snapshot is not None
        else None
    )

    if side == "BUY":
        quantity = _compute_buy_quantity(
            confidence_level=decision_package.forecast_confidence_level,
            usable_cash_eur=usable_cash_eur,
            portfolio_total_eur=portfolio_total_for_cap,
            fx_rate_eur_per_local=fx_rate_decimal,
            limit_price_local=limit_price_local,
        )
        if quantity <= 0:
            raise InsufficientCashError(
                "Onvoldoende cash voor positie op deze schaal. "
                "Verlaag het aantal of dismiss."
            )
    else:
        if held_quantity is None or held_quantity <= 0:
            raise NoPositionToSellError(
                f"Geen positie aanwezig om te verkopen ({decision_package.conid})."
            )
        quantity = _compute_sell_quantity(
            label=label, held_quantity=held_quantity
        )

    notional_local = (quantity * limit_price_local).quantize(_NOTIONAL_QUANTUM)
    notional_eur = (notional_local * fx_rate_decimal).quantize(
        _NOTIONAL_QUANTUM
    )

    composed_at = created_at or datetime.now(UTC)
    draft_id = f"adraft_{uuid4().hex}"

    audit_hash = _compute_audit_trail_hash(
        action_draft_id=draft_id,
        decision_package_id=decision_package.decision_package_id,
        ibkr_account_id=decision_package.ibkr_account_id,
        conid=decision_package.conid,
        side=side,
        quantity=quantity,
        limit_price_local=limit_price_local,
        notional_local=notional_local,
        notional_eur=notional_eur,
        fx_rate_at_creation=fx_rate_decimal,
        usable_cash_eur_at_creation=usable_cash_eur,
        held_quantity_at_creation=held_quantity,
        previous_draft_hash=previous_draft_hash,
    )

    exchange_value = decision_package.exchange or ""
    if not exchange_value:
        exchange_value = "UNKNOWN"

    return ActionDraftEntry(
        action_draft_id=draft_id,
        decision_package_id=decision_package.decision_package_id,
        forecast_run_id=decision_package.forecast_run_id,
        created_at=composed_at,
        created_by="user",
        ibkr_account_id=decision_package.ibkr_account_id,
        conid=decision_package.conid,
        symbol=decision_package.symbol,
        exchange=exchange_value,
        currency_local=decision_package.currency_local,
        side=side,
        quantity=quantity,
        order_type="LMT",
        limit_price_local=limit_price_local,
        time_in_force="DAY",
        notional_local=notional_local,
        notional_eur=notional_eur,
        fx_rate_at_creation=fx_rate_decimal,
        usable_cash_eur_at_creation=usable_cash_eur,
        held_quantity_at_creation=held_quantity,
        status="proposed",
        last_edited_at=None,
        user_approved_at=None,
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=user_note,
        superseded_by_decision_package_id=None,
        audit_trail_hash=audit_hash,
        previous_draft_hash=previous_draft_hash,
        safe_for_submission=False,
    )


def compose_action_draft_user_supplied(
    *,
    ibkr_account_id: str,
    conid: str,
    symbol: str,
    exchange: str,
    currency_local: str,
    side: str,
    quantity: Decimal,
    limit_price_local: Decimal,
    ibkr_cash_snapshot: IbkrAccountCashSnapshotRecord,
    ibkr_position_snapshot: IbkrPositionSnapshotRecord | None,
    fx_rate: FxRateRecord | None,
    user_buffer_eur: Decimal,
    approved_drafts_notional_eur: Decimal = Decimal("0"),
    user_note: str | None = None,
    previous_draft_hash: str | None = None,
    created_at: datetime | None = None,
) -> ActionDraftEntry:
    """Compose an Action Draft from user-supplied fields (no package).

    Used by the Volglijst quick-action flow when the user wants to act
    on an asset without going through a Decision Package detail page.
    SELL drafts still require a position; BUY drafts skip sizing
    entirely — the caller is responsible for the quantity.

    The cash + FX snapshots are captured at creation time so the
    ``usable_cash_eur_at_creation`` audit trail stays meaningful even
    if the user changes the buffer in Settings later.
    """

    if side not in {"BUY", "SELL"}:
        raise ValueError(f"side {side!r} must be 'BUY' or 'SELL'")
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if limit_price_local <= 0:
        raise ValueError("limit_price_local must be positive")

    fx_rate_decimal = _resolve_fx_rate(
        currency_local=currency_local, fx_rate=fx_rate
    )

    if ibkr_cash_snapshot.available_funds is None:
        raise ValueError(
            "ibkr_cash_snapshot.available_funds is required for "
            "Action Draft composition."
        )
    available_funds_eur = ibkr_cash_snapshot.available_funds
    if available_funds_eur < 0:
        available_funds_eur = Decimal("0")
    usable_cash_eur = (
        available_funds_eur
        - approved_drafts_notional_eur
        - user_buffer_eur
    )
    if usable_cash_eur < 0:
        usable_cash_eur = Decimal("0")

    held_quantity = (
        ibkr_position_snapshot.quantity
        if ibkr_position_snapshot is not None
        else None
    )
    if side == "SELL":
        if held_quantity is None or held_quantity <= 0:
            raise NoPositionToSellError(
                f"Geen positie aanwezig om te verkopen ({conid})."
            )

    notional_local = (quantity * limit_price_local).quantize(_NOTIONAL_QUANTUM)
    notional_eur = (notional_local * fx_rate_decimal).quantize(
        _NOTIONAL_QUANTUM
    )

    composed_at = created_at or datetime.now(UTC)
    draft_id = f"adraft_{uuid4().hex}"

    audit_hash = _compute_audit_trail_hash(
        action_draft_id=draft_id,
        decision_package_id=None,
        ibkr_account_id=ibkr_account_id,
        conid=conid,
        side=side,
        quantity=quantity,
        limit_price_local=limit_price_local,
        notional_local=notional_local,
        notional_eur=notional_eur,
        fx_rate_at_creation=fx_rate_decimal,
        usable_cash_eur_at_creation=usable_cash_eur,
        held_quantity_at_creation=held_quantity,
        previous_draft_hash=previous_draft_hash,
    )

    return ActionDraftEntry(
        action_draft_id=draft_id,
        decision_package_id=None,
        forecast_run_id=None,
        created_at=composed_at,
        created_by="user",
        ibkr_account_id=ibkr_account_id,
        conid=conid,
        symbol=symbol,
        exchange=exchange,
        currency_local=currency_local,
        side=side,
        quantity=quantity,
        order_type="LMT",
        limit_price_local=limit_price_local,
        time_in_force="DAY",
        notional_local=notional_local,
        notional_eur=notional_eur,
        fx_rate_at_creation=fx_rate_decimal,
        usable_cash_eur_at_creation=usable_cash_eur,
        held_quantity_at_creation=held_quantity,
        status="proposed",
        last_edited_at=None,
        user_approved_at=None,
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=user_note,
        superseded_by_decision_package_id=None,
        audit_trail_hash=audit_hash,
        previous_draft_hash=previous_draft_hash,
        safe_for_submission=False,
    )


def _compute_limit_price(
    *, current_price_local: Decimal, side: str
) -> Decimal:
    """BUY = close × (1 - 0.002); SELL = close × (1 + 0.002).

    Both rounded to 8 decimal places to match the storage schema.
    """

    if side == "BUY":
        return (
            current_price_local * (Decimal("1") - _LIMIT_PRICE_BIAS_BPS)
        ).quantize(_PRICE_QUANTUM)
    return (
        current_price_local * (Decimal("1") + _LIMIT_PRICE_BIAS_BPS)
    ).quantize(_PRICE_QUANTUM)


def _resolve_fx_rate(
    *, currency_local: str, fx_rate: FxRateRecord | None
) -> Decimal:
    if currency_local == "EUR":
        return Decimal("1")
    if fx_rate is None or fx_rate.rate <= 0:
        raise ValueError(
            f"FX rate ontbreekt voor {currency_local}; kan EUR-conversie "
            "niet uitvoeren."
        )
    return fx_rate.rate


def _compute_buy_quantity(
    *,
    confidence_level: str,
    usable_cash_eur: Decimal,
    portfolio_total_eur: Decimal,
    fx_rate_eur_per_local: Decimal,
    limit_price_local: Decimal,
) -> Decimal:
    """Cash-aware BUY sizing per Task 133 product lock §4."""

    target_pct = _BUY_TARGET_PCT_BY_CONFIDENCE.get(confidence_level)
    if target_pct is None:
        # Should be unreachable: the Decision Package
        # ``confidence_at_least_medium`` gate already filtered Laag.
        # Defending against a misconfigured caller — refuse the draft.
        raise UnsupportedDecisionPackageLabelError(
            f"Confidence level {confidence_level!r} not eligible for "
            "BUY sizing (must be Hoog or Gemiddeld)."
        )
    target_at_pct_eur = (portfolio_total_eur * target_pct).quantize(
        _NOTIONAL_QUANTUM
    )
    target_eur = min(target_at_pct_eur, usable_cash_eur)
    if target_eur <= 0:
        return Decimal("0")
    target_local = target_eur / fx_rate_eur_per_local
    # floor(target_local / limit_price_local) — whole shares only for V1.
    raw_quantity = target_local / limit_price_local
    return raw_quantity.quantize(_QUANTITY_QUANTUM, rounding=ROUND_DOWN)


def _compute_sell_quantity(
    *, label: str, held_quantity: Decimal
) -> Decimal:
    """SELL sizing — Verminderen = 25%, Verkopen = full exit."""

    if label == "Verkopen":
        return held_quantity.quantize(_QUANTITY_QUANTUM, rounding=ROUND_DOWN)
    if label == "Verminderen":
        portion = held_quantity * _SELL_VERMINDEREN_FRACTION
        return portion.quantize(_QUANTITY_QUANTUM, rounding=ROUND_DOWN)
    raise UnsupportedDecisionPackageLabelError(
        f"Unexpected SELL label {label!r}; expected Verminderen or Verkopen."
    )


def _decimal_to_canonical(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _compute_audit_trail_hash(
    *,
    action_draft_id: str,
    decision_package_id: str | None,
    ibkr_account_id: str,
    conid: str,
    side: str,
    quantity: Decimal,
    limit_price_local: Decimal,
    notional_local: Decimal,
    notional_eur: Decimal,
    fx_rate_at_creation: Decimal,
    usable_cash_eur_at_creation: Decimal,
    held_quantity_at_creation: Decimal | None,
    previous_draft_hash: str | None,
) -> str:
    """SHA-256 over canonical JSON of every draft-defining field.

    ``action_draft_id`` is included so two drafts with otherwise
    identical content still hash differently — drafts are not
    deduplicated like Decision Packages. ``created_at`` is excluded so
    the hash stays reproducible in tests.
    """

    canonical = {
        "action_draft_id": action_draft_id,
        "decision_package_id": decision_package_id,
        "ibkr_account_id": ibkr_account_id,
        "conid": conid,
        "side": side,
        "quantity": _decimal_to_canonical(quantity),
        "limit_price_local": _decimal_to_canonical(limit_price_local),
        "notional_local": _decimal_to_canonical(notional_local),
        "notional_eur": _decimal_to_canonical(notional_eur),
        "fx_rate_at_creation": _decimal_to_canonical(fx_rate_at_creation),
        "usable_cash_eur_at_creation": _decimal_to_canonical(
            usable_cash_eur_at_creation
        ),
        "held_quantity_at_creation": _decimal_to_canonical(
            held_quantity_at_creation
        ),
        "previous_draft_hash": previous_draft_hash,
    }
    canonical_bytes = json.dumps(
        canonical, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()
