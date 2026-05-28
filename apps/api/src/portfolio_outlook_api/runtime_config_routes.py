"""Editable IBKR connection + Claude AI settings API.

Surfaces the single ``runtime_config`` row (``config_id="default"``) so the
operator can edit the IBKR connection and the Claude AI explanation settings
from the dashboard Settings page instead of only via environment variables:

- ``GET /settings/connection``  -> current settings (DB row, or env defaults)
- ``PUT /settings/connection``  -> validate + upsert, return the saved values

The Claude API key is write-only: the response NEVER carries the value, only
``claude_ai_api_key_set: bool``. On PUT the key is optional — when omitted or
blank the previously-stored key is preserved.

Mirrors the storage-access patterns in ``error_routes.py``: ``_storage_provider()``
+ ``provider.checked_connection(...)`` + an explicit ``checked.connection.commit()``
on writes (the context manager does NOT auto-commit). The monetary budget is
serialised as a string so no float rounding leaks into the response.

``apply_runtime_config_overlay`` is the startup hook the API lifespan calls to
overlay the non-null DB values onto the settings singleton.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from ai_trading_agent_storage import (
    RuntimeConfigRecord,
    SqlAlchemyRuntimeConfigRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_CONFIG_ID = "default"

# Worker-side IBKR defaults used purely for display when no DB row exists yet.
_DEFAULT_IBKR_HOST = "127.0.0.1"
_DEFAULT_IBKR_PORT = 7497
_DEFAULT_IBKR_CLIENT_ID = 1


class ConnectionSettingsResponse(BaseModel):
    ibkr_enabled: bool
    ibkr_account_id: str | None
    ibkr_host: str | None
    ibkr_port: int | None
    ibkr_client_id: int | None
    ai_explanation_enabled: bool
    claude_ai_explanation_model: str | None
    claude_ai_budget_monthly_eur: str | None
    # Write-only key: never return the value, only whether one is stored.
    claude_ai_api_key_set: bool


class UpdateConnectionSettingsRequest(BaseModel):
    ibkr_enabled: bool
    ibkr_account_id: str | None = None
    ibkr_host: str | None = None
    ibkr_port: int | None = None
    ibkr_client_id: int | None = None
    ai_explanation_enabled: bool
    claude_ai_explanation_model: str | None = None
    claude_ai_budget_monthly_eur: Decimal | None = None
    # Optional secret: only sent when the operator types a new key. When
    # omitted or blank, the existing stored key is preserved.
    claude_ai_api_key: str | None = None


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(status_code=503, detail="Opslag is niet beschikbaar.")
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _budget_str(value: Decimal | None) -> str | None:
    """Canonical Decimal -> str: strip storage-scale padding (the column is
    ``Numeric(20, 6)`` so a stored ``50`` reads back as ``50.000000``) while
    keeping at least one fractional digit. Keeps the PUT response (built from
    the in-memory value) and a fresh GET (read back from the DB) identical, and
    never leaks a float."""

    if value is None:
        return None
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." not in text:
        text += ".0"
    return text


def _serialise(record: RuntimeConfigRecord) -> ConnectionSettingsResponse:
    return ConnectionSettingsResponse(
        ibkr_enabled=record.ibkr_enabled,
        ibkr_account_id=record.ibkr_account_id,
        ibkr_host=record.ibkr_host,
        ibkr_port=record.ibkr_port,
        ibkr_client_id=record.ibkr_client_id,
        ai_explanation_enabled=record.ai_explanation_enabled,
        claude_ai_explanation_model=record.claude_ai_explanation_model,
        claude_ai_budget_monthly_eur=_budget_str(record.claude_ai_budget_monthly_eur),
        claude_ai_api_key_set=bool(record.claude_ai_api_key),
    )


def _defaults_from_env() -> ConnectionSettingsResponse:
    """Fallback shown when no ``runtime_config`` row exists yet: the env/config
    defaults from the ``settings`` singleton plus the worker-side IBKR display
    defaults. The key value is never returned, only whether one is configured."""

    return ConnectionSettingsResponse(
        ibkr_enabled=bool(getattr(settings, "ibkr_enabled", False)),
        ibkr_account_id=getattr(settings, "ibkr_account_id_hint", None),
        ibkr_host=_DEFAULT_IBKR_HOST,
        ibkr_port=_DEFAULT_IBKR_PORT,
        ibkr_client_id=_DEFAULT_IBKR_CLIENT_ID,
        ai_explanation_enabled=bool(getattr(settings, "ai_explanation_enabled", False)),
        claude_ai_explanation_model=getattr(
            settings, "claude_ai_explanation_model", None
        ),
        claude_ai_budget_monthly_eur=_budget_str(
            getattr(settings, "claude_ai_budget_monthly_eur", None)
        ),
        claude_ai_api_key_set=bool(getattr(settings, "claude_ai_api_key", None)),
    )


@router.get("/settings/connection", response_model=ConnectionSettingsResponse)
def get_connection_settings() -> ConnectionSettingsResponse:
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            current = repo.get()
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    if current is None:
        return _defaults_from_env()
    return _serialise(current)


@router.put("/settings/connection", response_model=ConnectionSettingsResponse)
def update_connection_settings(
    payload: UpdateConnectionSettingsRequest,
) -> ConnectionSettingsResponse:
    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            # Optional key: keep the previously-stored value unless a new
            # non-empty key is supplied. Never overwrite a stored key with None.
            new_key = payload.claude_ai_api_key
            if new_key is not None and new_key.strip():
                stored_key: str | None = new_key
            elif existing is not None:
                stored_key = existing.claude_ai_api_key
            else:
                stored_key = None
            try:
                record = RuntimeConfigRecord(
                    config_id=_CONFIG_ID,
                    ibkr_enabled=payload.ibkr_enabled,
                    ibkr_account_id=payload.ibkr_account_id,
                    ibkr_host=payload.ibkr_host,
                    ibkr_port=payload.ibkr_port,
                    ibkr_client_id=payload.ibkr_client_id,
                    ai_explanation_enabled=payload.ai_explanation_enabled,
                    claude_ai_explanation_model=payload.claude_ai_explanation_model,
                    claude_ai_budget_monthly_eur=payload.claude_ai_budget_monthly_eur,
                    claude_ai_api_key=stored_key,
                    updated_at=now,
                )
            except (ValueError, InvalidOperation) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            repo.upsert(record)
            checked.connection.commit()
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _serialise(record)


def apply_runtime_config_overlay(
    settings_obj: Any, record: RuntimeConfigRecord
) -> None:
    """Overlay the non-null ``runtime_config`` values onto the settings object.

    Called at API startup so the operator-edited IBKR account + Claude AI
    settings take effect without an env change. Only non-null values are
    overlaid, so an empty field never clobbers a configured default.

    Worker-side IBKR host/port/client_id overlay is OUT OF SCOPE here — that is
    a follow-up tied to the durable worker session (the worker is not modified).
    """

    if record.ibkr_account_id is not None:
        settings_obj.ibkr_account_id_hint = record.ibkr_account_id
    if record.claude_ai_api_key is not None:
        settings_obj.claude_ai_api_key = record.claude_ai_api_key
    if record.claude_ai_explanation_model is not None:
        settings_obj.claude_ai_explanation_model = record.claude_ai_explanation_model
    if record.claude_ai_budget_monthly_eur is not None:
        settings_obj.claude_ai_budget_monthly_eur = record.claude_ai_budget_monthly_eur
    # ``ai_explanation_enabled`` is a non-null boolean column; the persisted
    # operator choice always wins once a row exists.
    settings_obj.ai_explanation_enabled = record.ai_explanation_enabled
