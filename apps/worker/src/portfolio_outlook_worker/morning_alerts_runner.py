"""Concrete morning-chain alerts runner.

Fires on every ``morning_briefing`` orchestrator event, AFTER the
worker-side market-data / forecasting / decision-package steps. Reads
today's suggestions for the operator's held positions, computes the
alert list via :func:`compute_morning_alerts`, and sends an email when
the same gates the digest path uses are satisfied:

1. Notifications master toggle is on,
2. At least one alert fired,
3. The relevant per-trigger preference is on, AND
4. SMTP config is complete + ``real_client_enabled``.

The runner is intentionally optimistic: missing positions, missing
suggestions, or storage errors all degrade to a zero-alert no-op
rather than raising. The orchestrator records the runner's return
dict in the audit row.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from ai_trading_agent_storage import (
    AssetSuggestionRecord,
    IbkrPositionSnapshotRecord,
    SqlAlchemyAssetSuggestionRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_worker.config import (
    NotificationSettings,
    StorageSettings,
)
from portfolio_outlook_worker.email_sender import (
    SmtpTransportConfig,
    send_email,
)
from portfolio_outlook_worker.morning_alerts import compute_morning_alerts

logger = logging.getLogger(__name__)


def _build_smtp_config(
    notifications: NotificationSettings,
) -> SmtpTransportConfig | None:
    if not (
        notifications.smtp_host
        and notifications.smtp_from
        and notifications.smtp_to
    ):
        return None
    return SmtpTransportConfig(
        host=notifications.smtp_host,
        port=int(notifications.smtp_port),
        username=notifications.smtp_username,
        password=notifications.smtp_password,
        from_address=notifications.smtp_from,
        to_address=notifications.smtp_to,
        use_tls=bool(notifications.smtp_use_tls),
    )


def _alert_is_enabled(
    alert: dict[str, object], notifications: NotificationSettings
) -> bool:
    """Reuse the digest-side per-trigger toggles. Morning alerts only
    map to one of them today (``high_confidence_sell``); the others
    forward-compat through the unknown-kind path."""

    kind = str(alert.get("kind", ""))
    if kind == "high_confidence_sell_morning":
        return notifications.send_on_high_confidence_sell
    if kind == "new_high_confidence_buy":
        # No dedicated buy toggle in v1 — piggyback on the master
        # ``email_enabled`` switch. Operators who want the buy
        # heads-up keep the master on; opt-out by turning master off.
        return True
    if kind == "morning_chain_failure":
        # Chain failures always reach the operator regardless of
        # per-trigger preferences (a silent failure is worse than a
        # missed buy-rec).
        return True
    return True


def _render_email_bodies(
    *,
    sendable_alerts: Sequence[dict[str, object]],
    today: str,
) -> tuple[str, str, str]:
    subject = (
        f"AI Trading Agent — ochtend-alerts ({today})"
    )

    plain_lines = [
        f"Ochtend-alerts voor {today}.",
        "",
    ]
    for alert in sendable_alerts:
        plain_lines.append(
            f"- [{alert.get('severity_nl')}] {alert.get('title_nl')}"
        )
        body_nl = alert.get("body_nl")
        if body_nl:
            plain_lines.append(f"  {body_nl}")
    plain_lines.append("")
    plain_lines.append(
        "Geen automatische actie — open de dashboard /suggesties pagina."
    )
    plain = "\n".join(plain_lines)

    html_items = "".join(
        f"<li><strong>[{alert.get('severity_nl')}]</strong> "
        f"{alert.get('title_nl')}<br/>"
        f"<span style='color:#374151'>{alert.get('body_nl')}</span></li>"
        for alert in sendable_alerts
    )
    html = (
        f"<p>Ochtend-alerts voor <strong>{today}</strong>.</p>"
        f"<ul>{html_items}</ul>"
        "<p style='color:#6b7280;font-size:12px;'>"
        "Geen automatische actie — open de dashboard /suggesties pagina.</p>"
    )

    return subject, plain, html


def _send_morning_email(
    *,
    alerts: Sequence[dict[str, object]],
    notifications: NotificationSettings,
    today_iso: str,
) -> dict[str, object]:
    if not notifications.email_enabled:
        return {"sent": False, "reason": "email_disabled"}
    if not alerts:
        return {"sent": False, "reason": "no_alerts"}
    sendable = [a for a in alerts if _alert_is_enabled(a, notifications)]
    if not sendable:
        return {
            "sent": False,
            "reason": "all_alerts_disabled_by_preference",
        }

    config = _build_smtp_config(notifications)
    if config is None:
        return {"sent": False, "reason": "smtp_config_incomplete"}

    subject, body_plain, body_html = _render_email_bodies(
        sendable_alerts=sendable, today=today_iso
    )
    result = send_email(
        config=config,
        subject=subject,
        body_plain=body_plain,
        body_html=body_html,
        real_client_enabled=notifications.real_client_enabled,
    )
    return {
        "sent": result.sent,
        "status": result.status,
        "detail_nl": result.detail_nl,
        "alerts_sent_count": len(sendable),
    }


class MorningAlertsRunner:
    """Implements ``_MorningAlertsRunnerProtocol``.

    Instantiated once at worker startup; re-used across every
    ``morning_briefing`` fire. Opens a short-lived storage connection
    per call so a long-running computation doesn't hold connections
    idle between fires.
    """

    def __init__(
        self,
        *,
        storage_settings: StorageSettings,
        notifications: NotificationSettings,
        now_provider: Any = lambda: datetime.now(UTC),
    ) -> None:
        self._storage_settings = storage_settings
        self._notifications = notifications
        self._now_provider = now_provider

    def run(
        self,
        *,
        ibkr_account_id: str,
        scheduled_run_id: str,
        chain_failed: bool = False,
        failure_reason_nl: str | None = None,
    ) -> dict[str, object]:
        if (
            not self._storage_settings.enabled
            or not self._storage_settings.database_url
        ):
            return {
                "sent_email": False,
                "alert_count": 0,
                "reason": "storage_unavailable",
            }
        try:
            provider = StorageConnectionProvider(
                build_database_connection_settings(
                    self._storage_settings.database_url
                )
            )
            with provider.checked_connection(require_writable=False) as checked:
                return self._compute(
                    checked.connection,
                    checked.readiness,
                    ibkr_account_id=ibkr_account_id,
                    chain_failed=chain_failed,
                    failure_reason_nl=failure_reason_nl,
                )
        except StorageConnectionError as exc:
            logger.warning("morning-alerts storage error: %s", exc)
            return {
                "sent_email": False,
                "alert_count": 0,
                "reason": "storage_connection_error",
                "detail": str(exc),
            }

    def _compute(
        self,
        connection: Any,
        readiness: Any,
        *,
        ibkr_account_id: str,
        chain_failed: bool,
        failure_reason_nl: str | None,
    ) -> dict[str, object]:
        ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(connection, readiness)
        suggestion_repo = SqlAlchemyAssetSuggestionRepository(
            connection, readiness
        )

        latest_run = ibkr_repo.get_latest_ibkr_sync_run()
        positions: list[IbkrPositionSnapshotRecord] = []
        if latest_run is not None:
            positions = list(
                ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id)
            )
        held_conids = {p.conid for p in positions if p.conid}

        suggestions: tuple[AssetSuggestionRecord, ...] = ()
        if held_conids:
            suggestions = suggestion_repo.list_latest_asset_suggestions_by_conids(
                tuple(held_conids)
            ).records

        alerts = compute_morning_alerts(
            suggestions=suggestions,
            held_conids=held_conids,
            chain_failed=chain_failed,
            failure_reason_nl=failure_reason_nl,
        )

        now = self._now_provider()
        email_summary = _send_morning_email(
            alerts=alerts,
            notifications=self._notifications,
            today_iso=now.date().isoformat(),
        )

        return {
            "alert_count": len(alerts),
            "position_count": len(positions),
            "suggestion_count": len(suggestions),
            "email": email_summary,
        }


__all__ = ["MorningAlertsRunner"]
