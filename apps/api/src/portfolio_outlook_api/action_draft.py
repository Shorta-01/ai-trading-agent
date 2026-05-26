"""Task 133: Action Draft API surface (seven routes).

* ``GET /action-draft/te-keuren?account_id=`` — list pending/approved.
* ``GET /action-draft/{id}`` — fetch one.
* ``POST /action-draft`` — create one (from Decision Package id or
  user-supplied fields).
* ``PATCH /action-draft/{id}`` — edit quantity / limit / user_note.
* ``POST /action-draft/{id}/approve`` — proposed/edited → user_approved.
* ``POST /action-draft/{id}/dismiss`` — dismiss with optional reason.
* ``POST /action-draft/{id}/delete`` — logical delete (row stays).

All routes:

* Pydantic v2 typed responses.
* Decimal-as-string on the wire (no float).
* HTTP 404 when the requested draft doesn't exist.
* HTTP 422 on invalid state transitions.
* HTTP 503 + locked Dutch body on storage unavailability.
* ``safe_for_submission`` hard-False in every response — Task 134 is
  the only code path allowed to flip it.

The actual IBKR submission is **out of scope** for this task. The
``approve`` route flips status to ``user_approved`` and stops there.
Task 134 will wire the real submit.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal, NoReturn

from ai_trading_agent_storage import (
    ActionDraftEntry,
    ActionDraftStateTransitionError,
    DecisionPackageEntry,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSubmissionLifecycleEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyDecisionPackageRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyIbkrSubmissionLifecycleRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    SqlAlchemyTradingSettingsRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from portfolio_outlook_worker.action_draft.composer import (
    InsufficientCashError,
    NoPositionToSellError,
    UnsupportedDecisionPackageLabelError,
    compose_action_draft_from_decision_package,
    compose_action_draft_user_supplied,
)
from pydantic import BaseModel, ConfigDict, Field

from portfolio_outlook_api.config import settings

router = APIRouter()

STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."


# ----------------------------------------------------------------------
# Pydantic response/request models.
# ----------------------------------------------------------------------


class ActionDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_draft_id: str
    decision_package_id: str | None
    forecast_run_id: str | None
    created_at: str
    created_by: Literal["user", "system"]
    ibkr_account_id: str
    conid: str
    symbol: str
    exchange: str
    currency_local: str
    side: Literal["BUY", "SELL"]
    quantity: str
    order_type: Literal["LMT"]
    limit_price_local: str
    time_in_force: Literal["DAY"]
    notional_local: str
    notional_eur: str
    fx_rate_at_creation: str
    usable_cash_eur_at_creation: str
    held_quantity_at_creation: str | None
    status: Literal[
        # Task 133 user-facing statuses.
        "proposed",
        "edited",
        "user_approved",
        "dismissed",
        "deleted",
        "superseded",
        # Task 134 IBKR lifecycle statuses.
        "submitted",
        "accepted",
        "working",
        "filled",
        "partially_filled",
        "cancelled",
        "rejected",
        "pending_cancellation",
        "awaiting_reply_timeout",
    ]
    last_edited_at: str | None
    user_approved_at: str | None
    dismissed_at: str | None
    deleted_at: str | None
    dismissed_reason: str | None
    user_note: str | None
    superseded_by_decision_package_id: str | None
    audit_trail_hash: str
    previous_draft_hash: str | None
    safe_for_submission: Literal[False] = False
    # Task 134 lifecycle fields surfaced through the API.
    submission_block_reason: str | None = None
    submission_started_at: str | None = None
    terminal_state_at: str | None = None


class ActionDraftListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str
    drafts: list[ActionDraftResponse]
    safe_for_submission: Literal[False] = False


class CreateActionDraftFromPackageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_package_id: str = Field(..., min_length=1)
    user_note: str | None = None


class CreateActionDraftUserSuppliedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str = Field(..., min_length=1)
    conid: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    exchange: str = Field(..., min_length=1)
    currency_local: str = Field(..., min_length=1)
    side: Literal["BUY", "SELL"]
    quantity: str = Field(..., min_length=1)
    limit_price_local: str = Field(..., min_length=1)
    user_note: str | None = None


class CreateActionDraftRequest(BaseModel):
    """Discriminated union: either ``decision_package_id`` or full fields."""

    model_config = ConfigDict(extra="forbid")

    decision_package_id: str | None = None
    user_note: str | None = None
    # User-supplied fields — required iff decision_package_id is None.
    ibkr_account_id: str | None = None
    conid: str | None = None
    symbol: str | None = None
    exchange: str | None = None
    currency_local: str | None = None
    side: Literal["BUY", "SELL"] | None = None
    quantity: str | None = None
    limit_price_local: str | None = None


class PatchActionDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: str | None = None
    limit_price_local: str | None = None
    user_note: str | None = None


class DismissActionDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


# ----------------------------------------------------------------------
# Serialization helpers.
# ----------------------------------------------------------------------


def _serialize_draft(entry: ActionDraftEntry) -> dict[str, object]:
    def _dec(value: Decimal | None) -> str | None:
        return None if value is None else str(value)

    def _ts(value: datetime | None) -> str | None:
        return None if value is None else value.isoformat()

    return {
        "action_draft_id": entry.action_draft_id,
        "decision_package_id": entry.decision_package_id,
        "forecast_run_id": entry.forecast_run_id,
        "created_at": entry.created_at.isoformat(),
        "created_by": entry.created_by,
        "ibkr_account_id": entry.ibkr_account_id,
        "conid": entry.conid,
        "symbol": entry.symbol,
        "exchange": entry.exchange,
        "currency_local": entry.currency_local,
        "side": entry.side,
        "quantity": str(entry.quantity),
        "order_type": entry.order_type,
        "limit_price_local": str(entry.limit_price_local),
        "time_in_force": entry.time_in_force,
        "notional_local": str(entry.notional_local),
        "notional_eur": str(entry.notional_eur),
        "fx_rate_at_creation": str(entry.fx_rate_at_creation),
        "usable_cash_eur_at_creation": str(entry.usable_cash_eur_at_creation),
        "held_quantity_at_creation": _dec(entry.held_quantity_at_creation),
        "status": entry.status,
        "last_edited_at": _ts(entry.last_edited_at),
        "user_approved_at": _ts(entry.user_approved_at),
        "dismissed_at": _ts(entry.dismissed_at),
        "deleted_at": _ts(entry.deleted_at),
        "dismissed_reason": entry.dismissed_reason,
        "user_note": entry.user_note,
        "superseded_by_decision_package_id": (
            entry.superseded_by_decision_package_id
        ),
        "audit_trail_hash": entry.audit_trail_hash,
        "previous_draft_hash": entry.previous_draft_hash,
        "safe_for_submission": False,
        "submission_block_reason": entry.submission_block_reason,
        "submission_started_at": _ts(entry.submission_started_at),
        "terminal_state_at": _ts(entry.terminal_state_at),
    }


def _raise_storage_unavailable() -> None:
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _to_decimal(value: str, field_name: str) -> Decimal:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail=f"Ongeldige decimale waarde voor {field_name}."
        ) from exc


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    assert storage.database_url is not None  # _raise_storage_unavailable raises above
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _configured_account_id() -> str | None:
    hint = getattr(settings, "ibkr_account_id_hint", None)
    if hint is None:
        return None
    text = str(hint).strip()
    return text or None


# ----------------------------------------------------------------------
# Routes (order matters — specific paths before catch-all ``/{id}``).
# ----------------------------------------------------------------------


@router.get(
    "/action-draft/te-keuren", response_model=ActionDraftListResponse
)
def list_te_keuren(
    account_id: str | None = None,
) -> dict[str, object]:
    """List drafts in ``proposed`` / ``edited`` / ``user_approved`` status.

    ``account_id`` is optional — when omitted, falls back to
    ``IBKR_ACCOUNT_ID_HINT`` (matches the decision-package convention).
    """

    effective_account = account_id or _configured_account_id()
    if effective_account is None:
        raise HTTPException(
            status_code=404,
            detail="Geen IBKR-rekening geconfigureerd.",
        )

    provider = _storage_provider()
    drafts_payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            entries = repo.list_te_keuren_for_account(effective_account)
            drafts_payload = [_serialize_draft(e) for e in entries]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "ibkr_account_id": effective_account,
        "drafts": drafts_payload,
        "safe_for_submission": False,
    }


@router.get("/action-draft/{action_draft_id}", response_model=ActionDraftResponse)
def read_action_draft(action_draft_id: str) -> dict[str, object]:
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            entry = repo.get_by_id(action_draft_id)
            if entry is None:
                raise HTTPException(
                    status_code=404, detail="Actiedraft niet gevonden."
                )
            return _serialize_draft(entry)
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _load_decision_package(
    *, repo: SqlAlchemyDecisionPackageRepository, decision_package_id: str
) -> DecisionPackageEntry:
    package = repo.get_by_id(decision_package_id)
    if package is None:
        raise HTTPException(
            status_code=404, detail="Decision Package niet gevonden."
        )
    return package


def _load_latest_cash_and_position(
    *,
    ibkr_repo: SqlAlchemyIbkrSyncSnapshotRepository,
    ibkr_account_id: str,
    conid: str,
) -> tuple[
    IbkrAccountCashSnapshotRecord, IbkrPositionSnapshotRecord | None
]:
    cash = ibkr_repo.get_latest_account_cash_snapshot(
        ibkr_account_id=ibkr_account_id
    )
    if cash is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Geen IBKR-cashsnapshot beschikbaar. "
                "Voer eerst een read-only sync uit."
            ),
        )
    position = ibkr_repo.get_latest_position_snapshot_for_conid(
        ibkr_account_id=ibkr_account_id, conid=conid
    )
    return cash, position


def _load_user_buffer_eur(
    *, settings_repo: SqlAlchemyTradingSettingsRepository
) -> Decimal:
    """Read ``user_buffer_eur`` from the persisted trading settings.

    Falls back to ``Decimal("0")`` when no settings row exists yet
    (Task 133 default per the user workshop answer).
    """

    read = settings_repo.get_settings("default")
    if not read.found or read.record is None:
        return Decimal("0")
    raw = read.record.user_strategy
    if not isinstance(raw, dict):
        return Decimal("0")
    value = raw.get("user_buffer_eur")
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


@router.post("/action-draft", response_model=ActionDraftResponse, status_code=201)
def create_action_draft(payload: CreateActionDraftRequest) -> dict[str, object]:
    """Create an Action Draft.

    Two creation paths:

    1. **From a Decision Package** — pass ``decision_package_id``. The
       composer applies cash-aware sizing (Task 133 product lock §4).
    2. **User-supplied** — pass all asset/order fields. No sizing logic
       is applied; ``quantity`` and ``limit_price_local`` are echoed.
    """

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            action_repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            dp_repo = SqlAlchemyDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            settings_repo = SqlAlchemyTradingSettingsRepository(
                checked.connection, checked.readiness
            )

            user_buffer = _load_user_buffer_eur(settings_repo=settings_repo)
            approved_drafts = action_repo.list_by_status(
                payload.ibkr_account_id or "", "user_approved"
            ) if payload.ibkr_account_id else ()
            # When linking to a package we don't have account_id on
            # the payload — derive from the package later. Approved-
            # drafts cash deduction stays at 0 for the user-supplied
            # path unless the request supplied an account.

            if payload.decision_package_id:
                package = _load_decision_package(
                    repo=dp_repo,
                    decision_package_id=payload.decision_package_id,
                )
                cash, position = _load_latest_cash_and_position(
                    ibkr_repo=ibkr_repo,
                    ibkr_account_id=package.ibkr_account_id,
                    conid=package.conid,
                )
                approved_drafts = action_repo.list_by_status(
                    package.ibkr_account_id, "user_approved"
                )
                approved_notional = sum(
                    (d.notional_eur for d in approved_drafts),
                    start=Decimal("0"),
                )
                try:
                    draft = compose_action_draft_from_decision_package(
                        decision_package=package,
                        ibkr_cash_snapshot=cash,
                        ibkr_position_snapshot=position,
                        fx_rate=None
                        if package.currency_local == "EUR"
                        else _load_fx_rate(
                            ibkr_repo=ibkr_repo,
                            currency_local=package.currency_local,
                        ),
                        user_buffer_eur=user_buffer,
                        portfolio_total_eur=cash.available_funds
                        if cash.available_funds is not None
                        else Decimal("0"),
                        approved_drafts_notional_eur=approved_notional,
                        user_note=payload.user_note,
                    )
                except (
                    InsufficientCashError,
                    NoPositionToSellError,
                    UnsupportedDecisionPackageLabelError,
                ) as exc:
                    raise HTTPException(
                        status_code=422, detail=str(exc)
                    ) from exc
            else:
                missing = [
                    name
                    for name, val in [
                        ("ibkr_account_id", payload.ibkr_account_id),
                        ("conid", payload.conid),
                        ("symbol", payload.symbol),
                        ("exchange", payload.exchange),
                        ("currency_local", payload.currency_local),
                        ("side", payload.side),
                        ("quantity", payload.quantity),
                        ("limit_price_local", payload.limit_price_local),
                    ]
                    if val is None
                ]
                if missing:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Ontbrekende velden voor user-supplied draft: "
                            + ", ".join(missing)
                        ),
                    )
                assert payload.ibkr_account_id is not None
                assert payload.conid is not None
                assert payload.symbol is not None
                assert payload.exchange is not None
                assert payload.currency_local is not None
                assert payload.side is not None
                assert payload.quantity is not None
                assert payload.limit_price_local is not None

                quantity = _to_decimal(payload.quantity, "quantity")
                limit_price = _to_decimal(
                    payload.limit_price_local, "limit_price_local"
                )
                cash, position = _load_latest_cash_and_position(
                    ibkr_repo=ibkr_repo,
                    ibkr_account_id=payload.ibkr_account_id,
                    conid=payload.conid,
                )
                approved_drafts = action_repo.list_by_status(
                    payload.ibkr_account_id, "user_approved"
                )
                approved_notional = sum(
                    (d.notional_eur for d in approved_drafts),
                    start=Decimal("0"),
                )
                try:
                    draft = compose_action_draft_user_supplied(
                        ibkr_account_id=payload.ibkr_account_id,
                        conid=payload.conid,
                        symbol=payload.symbol,
                        exchange=payload.exchange,
                        currency_local=payload.currency_local,
                        side=payload.side,
                        quantity=quantity,
                        limit_price_local=limit_price,
                        ibkr_cash_snapshot=cash,
                        ibkr_position_snapshot=position,
                        fx_rate=None
                        if payload.currency_local == "EUR"
                        else _load_fx_rate(
                            ibkr_repo=ibkr_repo,
                            currency_local=payload.currency_local,
                        ),
                        user_buffer_eur=user_buffer,
                        approved_drafts_notional_eur=approved_notional,
                        user_note=payload.user_note,
                    )
                except NoPositionToSellError as exc:
                    raise HTTPException(
                        status_code=422, detail=str(exc)
                    ) from exc

            stored = action_repo.append(draft)
            checked.connection.commit()
            return _serialize_draft(stored)
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _load_fx_rate(
    *,
    ibkr_repo: SqlAlchemyIbkrSyncSnapshotRepository,
    currency_local: str,
) -> NoReturn:
    """Resolve FX rate (local → EUR) from the latest fx-rate snapshot.

    The actual FX repository is module-scoped elsewhere; for V1 the
    composer accepts ``None`` and raises if a non-EUR currency is
    encountered without a rate. That's a 422 to the client — the user
    can read the message and retry once FX sync has run.
    """
    # In V1, the IBKR sync repo doesn't expose FX rates directly — the
    # caller must pre-sync. We surface a 422 with a Dutch message
    # rather than block silently.
    raise HTTPException(
        status_code=422,
        detail=(
            f"FX-koers ontbreekt voor {currency_local}. "
            "Voer eerst een EOD market-data sync uit."
        ),
    )


@router.patch(
    "/action-draft/{action_draft_id}", response_model=ActionDraftResponse
)
def patch_action_draft(
    action_draft_id: str, payload: PatchActionDraftRequest
) -> dict[str, object]:
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            current = repo.get_by_id(action_draft_id)
            if current is None:
                raise HTTPException(
                    status_code=404, detail="Actiedraft niet gevonden."
                )
            new_qty = (
                _to_decimal(payload.quantity, "quantity")
                if payload.quantity is not None
                else None
            )
            new_price = (
                _to_decimal(payload.limit_price_local, "limit_price_local")
                if payload.limit_price_local is not None
                else None
            )
            if new_qty is not None and new_qty <= 0:
                raise HTTPException(
                    status_code=422, detail="quantity moet > 0 zijn."
                )
            if new_price is not None and new_price <= 0:
                raise HTTPException(
                    status_code=422,
                    detail="limit_price_local moet > 0 zijn.",
                )
            # Recompute notionals when quantity or price changed.
            new_notional_local: Decimal | None = None
            new_notional_eur: Decimal | None = None
            if new_qty is not None or new_price is not None:
                effective_qty = new_qty if new_qty is not None else current.quantity
                effective_price = (
                    new_price
                    if new_price is not None
                    else current.limit_price_local
                )
                new_notional_local = effective_qty * effective_price
                new_notional_eur = (
                    new_notional_local * current.fx_rate_at_creation
                )
            try:
                updated = repo.update_fields(
                    action_draft_id=action_draft_id,
                    quantity=new_qty,
                    limit_price_local=new_price,
                    notional_local=new_notional_local,
                    notional_eur=new_notional_eur,
                    user_note=payload.user_note,
                    actor="user",
                    edited_at=datetime.now(UTC),
                )
            except ActionDraftStateTransitionError as exc:
                raise HTTPException(
                    status_code=422, detail=str(exc)
                ) from exc
            checked.connection.commit()
            return _serialize_draft(updated)
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


@router.post(
    "/action-draft/{action_draft_id}/approve",
    response_model=ActionDraftResponse,
)
def approve_action_draft(action_draft_id: str) -> dict[str, object]:
    """Flip ``proposed`` / ``edited`` to ``user_approved``.

    **Does NOT submit to IBKR** — Task 134 will wire the real submit.
    The locked Dutch info banner *"Goedgekeurd. IBKR-verzending wordt
    in een toekomstige update toegevoegd."* is rendered by the UI
    after a successful approve.
    """

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            current = repo.get_by_id(action_draft_id)
            if current is None:
                raise HTTPException(
                    status_code=404, detail="Actiedraft niet gevonden."
                )
            try:
                updated = repo.update_status(
                    action_draft_id=action_draft_id,
                    new_status="user_approved",
                    transition_actor="user",
                    transition_at=datetime.now(UTC),
                )
            except ActionDraftStateTransitionError as exc:
                raise HTTPException(
                    status_code=422, detail=str(exc)
                ) from exc
            checked.connection.commit()
            return _serialize_draft(updated)
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


@router.post(
    "/action-draft/{action_draft_id}/dismiss",
    response_model=ActionDraftResponse,
)
def dismiss_action_draft(
    action_draft_id: str, payload: DismissActionDraftRequest | None = None
) -> dict[str, object]:
    provider = _storage_provider()
    reason = payload.reason if payload is not None else None
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            current = repo.get_by_id(action_draft_id)
            if current is None:
                raise HTTPException(
                    status_code=404, detail="Actiedraft niet gevonden."
                )
            try:
                updated = repo.update_status(
                    action_draft_id=action_draft_id,
                    new_status="dismissed",
                    transition_actor="user",
                    transition_at=datetime.now(UTC),
                    dismissed_reason=reason,
                )
            except ActionDraftStateTransitionError as exc:
                raise HTTPException(
                    status_code=422, detail=str(exc)
                ) from exc
            checked.connection.commit()
            return _serialize_draft(updated)
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


@router.post(
    "/action-draft/{action_draft_id}/delete",
    response_model=ActionDraftResponse,
)
def delete_action_draft(action_draft_id: str) -> dict[str, object]:
    """Logical delete — the row stays for audit (Task 133 lock §3)."""

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            current = repo.get_by_id(action_draft_id)
            if current is None:
                raise HTTPException(
                    status_code=404, detail="Actiedraft niet gevonden."
                )
            try:
                updated = repo.update_status(
                    action_draft_id=action_draft_id,
                    new_status="deleted",
                    transition_actor="user",
                    transition_at=datetime.now(UTC),
                )
            except ActionDraftStateTransitionError as exc:
                raise HTTPException(
                    status_code=422, detail=str(exc)
                ) from exc
            checked.connection.commit()
            return _serialize_draft(updated)
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


# Statuses for which a user-initiated cancellation is legal (Task 134
# product lock §8). ``pending_cancellation`` itself is excluded — a
# second cancel click on an already-pending row is a no-op the UI
# should disable.
_CANCELLABLE_STATUSES = frozenset(
    {"submitted", "accepted", "working", "partially_filled"}
)


@router.post(
    "/action-draft/{action_draft_id}/cancel-submitted",
    response_model=ActionDraftResponse,
)
def cancel_submitted_action_draft(
    action_draft_id: str,
) -> dict[str, object]:
    """Task 134 product lock §8 — one-way user-initiated cancellation.

    Valid only for in-flight statuses. Transitions the draft to
    ``pending_cancellation`` and writes one ``ibkr_submission_lifecycle``
    row tagged ``event_type='cancellation_request'``. **Does not call
    IBKR** — the worker picks the row up from the database on its
    next sweep tick and issues ``ib.cancelOrder()`` from the
    long-lived TWS session (locked: only the worker owns the socket).
    The actual ``cancelled`` status comes from the IBKR callback the
    worker's lifecycle handler processes.
    """

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            lifecycle_repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
                checked.connection, checked.readiness
            )
            audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(
                checked.connection, checked.readiness
            )
            current = repo.get_by_id(action_draft_id)
            if current is None:
                raise HTTPException(
                    status_code=404, detail="Actiedraft niet gevonden."
                )
            if current.status not in _CANCELLABLE_STATUSES:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Cancel niet toegestaan: draft is niet in een "
                        f"actief IBKR-status (status={current.status!r})."
                    ),
                )

            now = datetime.now(UTC)
            try:
                updated = repo.apply_lifecycle_transition(
                    action_draft_id=action_draft_id,
                    new_status="pending_cancellation",
                    transitioned_at=now,
                )
            except ActionDraftStateTransitionError as exc:
                raise HTTPException(
                    status_code=422, detail=str(exc)
                ) from exc

            # Look up the perm_id from the most recent placed audit
            # row so the lifecycle entry references the right IBKR
            # order. The worker uses this perm_id when issuing the
            # actual ``cancelOrder``.
            perm_id = _lookup_perm_id_for_draft(
                audit_repo=audit_repo,
                action_draft_id=action_draft_id,
            )
            lifecycle_repo.append(
                IbkrSubmissionLifecycleEntry(
                    action_draft_id=action_draft_id,
                    event_at=now,
                    ibkr_perm_id=perm_id,
                    event_type="cancellation_request",
                    from_status=current.status,
                    to_status=updated.status,
                    ibkr_raw_status=None,
                    fill_price_local=None,
                    fill_quantity=None,
                    commission=None,
                    commission_currency=None,
                    raw_callback_json={
                        "source": "user_api_cancel",
                        "from_status": current.status,
                    },
                )
            )
            checked.connection.commit()
            return _serialize_draft(updated)
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _lookup_perm_id_for_draft(
    *,
    audit_repo: SqlAlchemyIbkrSubmissionAuditRepository,
    action_draft_id: str,
) -> int:
    """Look up the perm_id from the most recent placed submission row.

    The cancel route needs it for the lifecycle audit row. If no placed
    submission exists yet (shouldn't happen because the draft was at
    submitted+), we return 0 as a sentinel — the worker will reconcile
    on its next tick.
    """

    rows = audit_repo.list_for_draft(action_draft_id)
    for row in reversed(rows):
        if row.result == "placed" and row.ibkr_perm_id is not None:
            return row.ibkr_perm_id
    return 0


__all__ = [
    "ActionDraftListResponse",
    "ActionDraftResponse",
    "CreateActionDraftRequest",
    "DismissActionDraftRequest",
    "PatchActionDraftRequest",
    "router",
]
