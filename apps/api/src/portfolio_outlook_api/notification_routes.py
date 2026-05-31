"""Notification settings + test-email endpoints (PR K).

Surfaces the SMTP transport config + per-trigger preferences. The
SMTP password is write-only: the GET response always carries
``smtp_password_set: bool`` instead of the value, and PUT requests
with a blank password preserve whatever is already stored.

Three endpoints:
- ``GET  /settings/notifications``  — current config + prefs
- ``PUT  /settings/notifications``  — save the operator's edits
- ``POST /settings/notifications/test-email`` — send a test email so
  the operator can verify the SMTP config works before relying on it

The actual digest-on-market-close email path is wired in a follow-up
PR; this PR ships the transport + operator surface only.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
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
from portfolio_outlook_api.email_sender import (
    SmtpTransportConfig,
    send_email,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_CONFIG_ID = "default"


class NotificationSettingsResponse(BaseModel):
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_from: str | None
    smtp_to: str | None
    smtp_use_tls: bool
    smtp_password_set: bool
    notifications_email_enabled: bool
    notifications_email_real_client_enabled: bool
    notification_send_on_nav_drop: bool
    notification_send_on_position_drop: bool
    notification_send_on_high_confidence_sell: bool
    help_nl: str


class UpdateNotificationSettingsRequest(BaseModel):
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    # Write-only. Blank/omitted preserves the existing stored password.
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None
    smtp_use_tls: bool = True
    notifications_email_enabled: bool = False
    notification_send_on_nav_drop: bool = True
    notification_send_on_position_drop: bool = True
    notification_send_on_high_confidence_sell: bool = True


class TestEmailResponse(BaseModel):
    sent: bool
    status: str
    detail_nl: str
    used_host: str | None


_NOTIFICATIONS_HELP_NL = (
    "Configureer SMTP zodat het systeem e-mails kan sturen wanneer "
    "iets belangrijks gebeurt: een NAV-daling, een grote dip op een "
    "positie, of een hoge-zekerheid verkoop-suggestie. Sla je SMTP-"
    "instellingen eerst op, gebruik dan de 'Test e-mail' knop om te "
    "verifiëren dat de verbinding werkt. De ``smtp_password`` wordt "
    "nooit teruggegeven via de API — alleen of er een waarde is "
    "opgeslagen. Tip: voor Gmail gebruik een app-specifiek password."
)


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise StorageConnectionError("storage_disabled")
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _notification_payload(
    record: RuntimeConfigRecord | None,
) -> NotificationSettingsResponse:
    def _str(name: str, default: str | None = None) -> str | None:
        if record is not None and getattr(record, name, None) is not None:
            return getattr(record, name)
        return getattr(settings, name, default)

    def _int(name: str, default: int) -> int:
        if record is not None and getattr(record, name, None) is not None:
            return int(getattr(record, name))
        return int(getattr(settings, name, default))

    def _bool(name: str, default: bool) -> bool:
        if record is not None and getattr(record, name, None) is not None:
            return bool(getattr(record, name))
        return bool(getattr(settings, name, default))

    password_present = False
    if record is not None and record.smtp_password:
        password_present = True
    elif getattr(settings, "smtp_password", None):
        password_present = True

    return NotificationSettingsResponse(
        smtp_host=_str("smtp_host"),
        smtp_port=_int("smtp_port", 587),
        smtp_username=_str("smtp_username"),
        smtp_from=_str("smtp_from"),
        smtp_to=_str("smtp_to"),
        smtp_use_tls=_bool("smtp_use_tls", True),
        smtp_password_set=password_present,
        notifications_email_enabled=_bool("notifications_email_enabled", False),
        notifications_email_real_client_enabled=bool(
            settings.notifications_email_real_client_enabled
        ),
        notification_send_on_nav_drop=_bool(
            "notification_send_on_nav_drop", True
        ),
        notification_send_on_position_drop=_bool(
            "notification_send_on_position_drop", True
        ),
        notification_send_on_high_confidence_sell=_bool(
            "notification_send_on_high_confidence_sell", True
        ),
        help_nl=_NOTIFICATIONS_HELP_NL,
    )


@router.get(
    "/settings/notifications", response_model=NotificationSettingsResponse
)
def get_notification_settings() -> NotificationSettingsResponse:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _notification_payload(None)
    try:
        provider = _storage_provider()
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            current = repo.get()
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _notification_payload(current)


@router.put(
    "/settings/notifications", response_model=NotificationSettingsResponse
)
def update_notification_settings(
    payload: UpdateNotificationSettingsRequest,
) -> NotificationSettingsResponse:
    if payload.smtp_port < 1 or payload.smtp_port > 65535:
        raise HTTPException(
            status_code=422,
            detail="SMTP-poort moet tussen 1 en 65535 liggen.",
        )

    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            # Write-only password: blank/None preserves the stored
            # value. Mirrors the existing claude_ai_api_key pattern.
            stored_password: str | None = None
            if payload.smtp_password and payload.smtp_password.strip():
                stored_password = payload.smtp_password
            elif existing is not None:
                stored_password = existing.smtp_password

            record = _carry_existing_into_record(
                existing,
                now=now,
                payload=payload,
                stored_password=stored_password,
            )
            repo.upsert(record)
            checked.connection.commit()
            # Reflect onto the in-process settings singleton so the
            # test-email endpoint picks up the new values immediately.
            settings.smtp_host = payload.smtp_host
            settings.smtp_port = payload.smtp_port
            settings.smtp_username = payload.smtp_username
            if stored_password is not None:
                settings.smtp_password = stored_password
            settings.smtp_from = payload.smtp_from
            settings.smtp_to = payload.smtp_to
            settings.smtp_use_tls = payload.smtp_use_tls
            settings.notifications_email_enabled = (
                payload.notifications_email_enabled
            )
            settings.notification_send_on_nav_drop = (
                payload.notification_send_on_nav_drop
            )
            settings.notification_send_on_position_drop = (
                payload.notification_send_on_position_drop
            )
            settings.notification_send_on_high_confidence_sell = (
                payload.notification_send_on_high_confidence_sell
            )
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _notification_payload(record)


@router.post(
    "/settings/notifications/test-email", response_model=TestEmailResponse
)
def send_test_email() -> TestEmailResponse:
    """Send one test email using the currently-saved SMTP settings.

    Honours ``notifications_email_real_client_enabled`` — when False
    this returns a ``stubbed`` result without opening an SMTP session.
    That's the safe default: a fresh deploy with SMTP creds saved but
    no operator opt-in can't accidentally email anyone.
    """

    if not settings.smtp_host or not settings.smtp_from or not settings.smtp_to:
        return TestEmailResponse(
            sent=False,
            status="config_missing",
            detail_nl=(
                "SMTP-host, afzender of ontvanger ontbreekt. Vul de "
                "verbinding-instellingen aan en sla op."
            ),
            used_host=settings.smtp_host,
        )

    config = SmtpTransportConfig(
        host=settings.smtp_host,
        port=int(settings.smtp_port),
        username=settings.smtp_username,
        password=settings.smtp_password,
        from_address=settings.smtp_from,
        to_address=settings.smtp_to,
        use_tls=bool(settings.smtp_use_tls),
    )
    result = send_email(
        config=config,
        subject="AI Trading Agent — test e-mail",
        body_plain=(
            "Dit is een test-e-mail vanuit de AI Trading Agent.\n\n"
            "Als je deze ontvangt, werkt de SMTP-verbinding correct."
        ),
        body_html=(
            "<p>Dit is een <strong>test-e-mail</strong> vanuit de AI "
            "Trading Agent.</p><p>Als je deze ontvangt, werkt de "
            "SMTP-verbinding correct.</p>"
        ),
        real_client_enabled=settings.notifications_email_real_client_enabled,
    )
    return TestEmailResponse(
        sent=result.sent,
        status=result.status,
        detail_nl=result.detail_nl,
        used_host=result.used_host,
    )


def _carry_existing_into_record(
    existing: RuntimeConfigRecord | None,
    *,
    now: datetime,
    payload: UpdateNotificationSettingsRequest,
    stored_password: str | None,
) -> RuntimeConfigRecord:
    """Carry every existing field forward except the notification ones.
    Mirrors the carry-over pattern every other settings PUT uses, so
    saving notifications never wipes another section."""

    def _carry(name: str, default: Any = None) -> Any:
        if existing is None:
            return default
        return getattr(existing, name, default)

    return RuntimeConfigRecord(
        config_id=_CONFIG_ID,
        ibkr_enabled=_carry("ibkr_enabled", False),
        ibkr_account_id=_carry("ibkr_account_id"),
        ibkr_host=_carry("ibkr_host"),
        ibkr_port=_carry("ibkr_port"),
        ibkr_client_id=_carry("ibkr_client_id"),
        ai_explanation_enabled=_carry("ai_explanation_enabled", False),
        claude_ai_explanation_model=_carry("claude_ai_explanation_model"),
        claude_ai_budget_monthly_eur=_carry("claude_ai_budget_monthly_eur"),
        claude_ai_api_key=_carry("claude_ai_api_key"),
        updated_at=now,
        universe_scan_index_codes=_carry("universe_scan_index_codes"),
        default_buy_value_eur=_carry("default_buy_value_eur"),
        default_top_up_pct=_carry("default_top_up_pct"),
        default_reduce_pct=_carry("default_reduce_pct"),
        max_sector_pct=_carry("max_sector_pct"),
        cost_dominates_ratio=_carry("cost_dominates_ratio"),
        suggestion_valid_minutes=_carry("suggestion_valid_minutes"),
        scheduler_daily_briefing_cron=_carry("scheduler_daily_briefing_cron"),
        ibkr_sync_interval_minutes=_carry("ibkr_sync_interval_minutes"),
        forecast_history_lookback_days=_carry("forecast_history_lookback_days"),
        forecast_minimum_bars_required=_carry("forecast_minimum_bars_required"),
        daily_briefing_lookback_hours=_carry("daily_briefing_lookback_hours"),
        universe_scan_cache_ttl_hours=_carry("universe_scan_cache_ttl_hours"),
        sweep_interval_seconds=_carry("sweep_interval_seconds"),
        sweep_retry_max_attempts=_carry("sweep_retry_max_attempts"),
        sweep_retry_backoff_seconds=_carry("sweep_retry_backoff_seconds"),
        sweep_alert_after_consecutive_errors=_carry(
            "sweep_alert_after_consecutive_errors"
        ),
        eodhd_rate_limit_per_second=_carry("eodhd_rate_limit_per_second"),
        ensemble_weight_strategy=_carry("ensemble_weight_strategy"),
        gbm_drift_window_days=_carry("gbm_drift_window_days"),
        action_draft_approval_valid_minutes=_carry(
            "action_draft_approval_valid_minutes"
        ),
        ai_explanation_provider_code=_carry("ai_explanation_provider_code"),
        sharpe_strong_threshold=_carry("sharpe_strong_threshold"),
        sharpe_slight_threshold=_carry("sharpe_slight_threshold"),
        forecast_horizon_trading_days=_carry("forecast_horizon_trading_days"),
        forecast_ensemble_enabled=_carry("forecast_ensemble_enabled"),
        suggestions_risk_profile=_carry("suggestions_risk_profile"),
        universe_set=_carry("universe_set"),
        market_data_provider=_carry("market_data_provider"),
        market_data_sync_enabled=_carry("market_data_sync_enabled"),
        ibkr_market_data_enabled=_carry("ibkr_market_data_enabled"),
        ibkr_market_data_type=_carry("ibkr_market_data_type"),
        ibkr_paper_order_submission_enabled=_carry(
            "ibkr_paper_order_submission_enabled"
        ),
        submission_sweep_enabled=_carry("submission_sweep_enabled"),
        cancel_sweep_enabled=_carry("cancel_sweep_enabled"),
        morning_chain_after_pre_briefing=_carry(
            "morning_chain_after_pre_briefing"
        ),
        forecast_valid_minutes=_carry("forecast_valid_minutes"),
        decision_packages_valid_minutes=_carry(
            "decision_packages_valid_minutes"
        ),
        prediction_diary_inconclusive_tolerance_pct=_carry(
            "prediction_diary_inconclusive_tolerance_pct"
        ),
        gbm_regime_shift_enabled=_carry("gbm_regime_shift_enabled"),
        gbm_regime_shift_threshold_pct=_carry(
            "gbm_regime_shift_threshold_pct"
        ),
        scheduler_per_market_close_digest_enabled=_carry(
            "scheduler_per_market_close_digest_enabled"
        ),
        scheduler_per_market_open_alerts_enabled=_carry(
            "scheduler_per_market_open_alerts_enabled"
        ),
        smtp_host=payload.smtp_host,
        smtp_port=payload.smtp_port,
        smtp_username=payload.smtp_username,
        smtp_password=stored_password,
        smtp_from=payload.smtp_from,
        smtp_to=payload.smtp_to,
        smtp_use_tls=payload.smtp_use_tls,
        notifications_email_enabled=payload.notifications_email_enabled,
        notification_send_on_nav_drop=payload.notification_send_on_nav_drop,
        notification_send_on_position_drop=(
            payload.notification_send_on_position_drop
        ),
        notification_send_on_high_confidence_sell=(
            payload.notification_send_on_high_confidence_sell
        ),
    )


__all__ = [
    "NotificationSettingsResponse",
    "TestEmailResponse",
    "UpdateNotificationSettingsRequest",
    "router",
]
