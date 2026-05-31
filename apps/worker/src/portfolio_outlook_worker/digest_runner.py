"""Concrete end-of-day digest runner — fired by the orchestrator on
each ``market_close`` event.

Pulls today's persisted state from storage, computes the digest payload
via :func:`compute_daily_digest_payload`, upserts the result, and (when
notifications are enabled) renders + sends the digest email.

Graceful degradation is intentional: missing NAV, missing positions,
or missing suggestions all result in a ``partial`` or empty-section
digest, never an exception. The orchestrator records the runner's
return value in the audit row; failures bubble up there, not into the
scheduler.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from ai_trading_agent_storage import (
    AssetActionDraftRecord,
    AssetSuggestionRecord,
    DailyDigestRecord,
    IbkrNavSnapshotRecord,
    IbkrPositionSnapshotRecord,
    MarketDataLatestSnapshotRecord,
    SqlAlchemyAssetActionDraftRepository,
    SqlAlchemyAssetSuggestionRepository,
    SqlAlchemyDailyDigestRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    SqlAlchemyMarketDataSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_worker.api_trigger import compose_alert_summary
from portfolio_outlook_worker.config import (
    NotificationSettings,
    StorageSettings,
)
from portfolio_outlook_worker.daily_digest import compute_daily_digest_payload
from portfolio_outlook_worker.email_sender import (
    SmtpTransportConfig,
    send_email,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _PositionWithPnl:
    """Adapter struct: position fields the digest compute function
    reads via ``getattr``. Carries the joined PnL so the compute layer
    doesn't need to know about market-data snapshots."""

    symbol: str
    currency: str
    pnl_pct: Decimal | None
    pnl_abs: Decimal | None


def _join_positions_with_pnl(
    positions: Sequence[IbkrPositionSnapshotRecord],
    market_snapshots: Sequence[MarketDataLatestSnapshotRecord],
) -> list[_PositionWithPnl]:
    """Compute today's PnL per position from the latest market-data
    snapshot. Positions without a corresponding snapshot or a positive
    average cost yield ``None`` PnL (compute_daily_digest_payload then
    silently drops them from the top-winner/loser lists)."""

    snapshot_by_conid: dict[str, MarketDataLatestSnapshotRecord] = {}
    for snapshot in market_snapshots:
        snapshot_by_conid[snapshot.ibkr_conid] = snapshot

    out: list[_PositionWithPnl] = []
    for position in positions:
        last_price: Decimal | None = None
        if position.conid is not None:
            matched = snapshot_by_conid.get(position.conid)
            if matched is not None:
                # Prefer last_price; fall back to close_price (EOD).
                last_price = matched.last_price or matched.close_price
        pnl_pct: Decimal | None = None
        pnl_abs: Decimal | None = None
        avg_cost = position.average_cost
        if (
            last_price is not None
            and avg_cost is not None
            and avg_cost > 0
            and position.quantity is not None
        ):
            price_delta = last_price - avg_cost
            pnl_pct = (price_delta / avg_cost) * Decimal("100")
            pnl_abs = price_delta * position.quantity
        out.append(
            _PositionWithPnl(
                symbol=position.symbol or "?",
                currency=position.currency or "USD",
                pnl_pct=pnl_pct,
                pnl_abs=pnl_abs,
            )
        )
    return out


def _resolve_nav_pair(
    nav_snapshots: Sequence[IbkrNavSnapshotRecord],
) -> tuple[Decimal | None, Decimal | None, str]:
    """Pick today's NAV (latest) and yesterday's NAV (most recent that
    pre-dates today's). The snapshots are passed in ascending recorded
    order; iterating from the end gives the latest first."""

    if not nav_snapshots:
        return None, None, "EUR"
    latest = nav_snapshots[-1]
    today_nav = latest.nav_value
    base_currency = latest.base_currency or "EUR"
    today_date = latest.recorded_at.date()
    prev_nav: Decimal | None = None
    for snapshot in reversed(nav_snapshots[:-1]):
        if snapshot.recorded_at.date() < today_date:
            prev_nav = snapshot.nav_value
            break
    return today_nav, prev_nav, base_currency


def _filter_today_drafts(
    drafts: Iterable[AssetActionDraftRecord], today: date
) -> list[AssetActionDraftRecord]:
    return [d for d in drafts if d.created_at.date() == today]


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
    kind = str(alert.get("kind", ""))
    if kind == "nav_drop":
        return notifications.send_on_nav_drop
    if kind == "position_drop":
        return notifications.send_on_position_drop
    if kind == "high_confidence_sell":
        return notifications.send_on_high_confidence_sell
    # Unknown alert kinds default to sending (forward-compatible: new
    # triggers shipped without a matching pref flag still reach the
    # operator).
    return True


def _render_email_bodies(
    *,
    digest: DailyDigestRecord,
    sendable_alerts: Sequence[dict[str, object]],
    ai_summary_nl: str | None = None,
) -> tuple[str, str, str]:
    """Build (subject, plain_body, html_body) for the digest email.

    When ``ai_summary_nl`` is non-empty it's prepended to the body as
    a Dutch summary header. The deterministic template body is always
    included below it, so a missing / blocked / unavailable AI summary
    is invisible to the operator — same email shape as before.
    """

    nav = digest.nav_summary_json or {}
    delta_pct = nav.get("delta_pct")
    delta_str = f"{delta_pct}%" if delta_pct is not None else "—"
    currency = nav.get("currency", "EUR")

    subject = (
        f"AI Trading Agent — einde-dag digest "
        f"({digest.market_code}, {digest.briefing_date.isoformat()})"
    )

    alert_lines = "\n".join(
        f"- [{a.get('severity_nl')}] {a.get('title_nl')}\n  {a.get('body_nl')}"
        for a in sendable_alerts
    )
    plain_summary = (
        f"AI-samenvatting:\n{ai_summary_nl.strip()}\n\n" if ai_summary_nl else ""
    )
    plain = (
        plain_summary
        + f"Einde-dag digest voor {digest.market_code} op "
        + f"{digest.briefing_date.isoformat()}.\n\n"
        + f"Portfolio-NAV verandering: {delta_str} ({currency}).\n"
        + f"Suggesties vandaag: {digest.suggestions_summary_json.get('total', 0)}.\n"
        + "Action drafts vandaag: "
        + f"{digest.action_drafts_summary_json.get('created_today', 0)} aangemaakt.\n\n"
        + f"Aandachtspunten:\n{alert_lines or '(geen)'}\n\n"
        + "Open de dashboard /digest pagina voor het volledige overzicht."
    )

    alert_html = "".join(
        f"<li><strong>[{a.get('severity_nl')}]</strong> "
        f"{a.get('title_nl')}<br/><span style='color:#374151'>"
        f"{a.get('body_nl')}</span></li>"
        for a in sendable_alerts
    )
    html_summary = (
        f"<p><strong>AI-samenvatting:</strong><br/>"
        f"<span style='color:#1f2937'>{ai_summary_nl.strip()}</span></p>"
        if ai_summary_nl
        else ""
    )
    html = (
        html_summary
        + f"<p>Einde-dag digest voor <strong>{digest.market_code}</strong> "
        + f"op <strong>{digest.briefing_date.isoformat()}</strong>.</p>"
        + "<ul>"
        + f"<li>Portfolio-NAV verandering: <strong>{delta_str}</strong> "
        + f"({currency})</li>"
        + "<li>Suggesties vandaag: "
        + f"<strong>{digest.suggestions_summary_json.get('total', 0)}</strong></li>"
        + "<li>Action drafts vandaag: "
        + f"<strong>{digest.action_drafts_summary_json.get('created_today', 0)}"
        + "</strong> aangemaakt</li>"
        + "</ul>"
        + "<h3>Aandachtspunten</h3>"
        + (f"<ul>{alert_html}</ul>" if alert_html else "<p>(geen)</p>")
        + "<p style='color:#6b7280;font-size:12px;'>"
        + "Open de dashboard /digest pagina voor het volledige overzicht.</p>"
    )

    return subject, plain, html


def _build_digest_context_text(digest: DailyDigestRecord) -> str:
    """Compose the deterministic context block used as AI input evidence.

    Every number in this block must also appear in the alert lines or
    be drawn directly from the persisted digest record — the hallucination
    guard refuses any AI output that introduces a new numeric token.
    """

    nav = digest.nav_summary_json or {}
    delta_pct = nav.get("delta_pct")
    delta_str = f"{delta_pct}%" if delta_pct is not None else "—"
    currency = nav.get("currency", "EUR")
    return (
        f"Markt: {digest.market_code}. "
        f"Datum: {digest.briefing_date.isoformat()}. "
        f"NAV verandering: {delta_str} ({currency}). "
        f"Suggesties: {digest.suggestions_summary_json.get('total', 0)}. "
        f"Action drafts: "
        f"{digest.action_drafts_summary_json.get('created_today', 0)}."
    )


def _maybe_compose_ai_summary(
    *,
    digest: DailyDigestRecord,
    sendable_alerts: Sequence[dict[str, object]],
    api_base_url: str | None,
    api_request_timeout_seconds: float,
    notifications: NotificationSettings,
) -> str | None:
    """Optionally fetch a Claude-composed Dutch header for the email.

    Returns the summary string when the AI path produced a guarded,
    non-empty result; ``None`` in every other case so the caller sends
    the template-only email. Never raises.
    """

    if not notifications.ai_email_summary_enabled:
        return None
    if not sendable_alerts:
        return None
    alert_lines = [
        f"- [{a.get('severity_nl')}] {a.get('title_nl')}: {a.get('body_nl')}"
        for a in sendable_alerts
    ]
    context_text = _build_digest_context_text(digest)
    body = compose_alert_summary(
        base_url=api_base_url,
        timeout_seconds=api_request_timeout_seconds,
        kind="digest",
        context_text=context_text,
        alert_lines=alert_lines,
    )
    if not body or body.get("status") != "generated":
        return None
    summary_nl = body.get("summary_nl")
    if isinstance(summary_nl, str) and summary_nl.strip():
        return summary_nl.strip()
    return None


def _send_digest_email(
    *,
    digest: DailyDigestRecord,
    notifications: NotificationSettings,
    api_base_url: str | None,
    api_request_timeout_seconds: float,
) -> dict[str, object]:
    """Decide whether to send + send + return audit dict. The decision
    matrix collapses to: notifications master on, at least one alert
    fired, at least one of those alerts is enabled by its trigger
    preference."""

    if not notifications.email_enabled:
        return {"sent": False, "reason": "email_disabled"}
    alerts = list(digest.alerts_json or [])
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

    ai_summary_nl = _maybe_compose_ai_summary(
        digest=digest,
        sendable_alerts=sendable,
        api_base_url=api_base_url,
        api_request_timeout_seconds=api_request_timeout_seconds,
        notifications=notifications,
    )
    subject, body_plain, body_html = _render_email_bodies(
        digest=digest, sendable_alerts=sendable, ai_summary_nl=ai_summary_nl
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
        "ai_summary_used": ai_summary_nl is not None,
    }


class DailyDigestRunner:
    """Implements ``_DigestRunnerProtocol``.

    One instance is registered with the orchestrator at worker
    startup and re-used across every ``market_close`` fire. Each call
    opens its own short-lived storage connection so a long-running
    digest doesn't hold connections idle.
    """

    def __init__(
        self,
        *,
        storage_settings: StorageSettings,
        notifications: NotificationSettings,
        now_provider: Any = lambda: datetime.now(UTC),
        api_base_url: str | None = None,
        api_request_timeout_seconds: float = 30.0,
    ) -> None:
        self._storage_settings = storage_settings
        self._notifications = notifications
        self._now_provider = now_provider
        self._api_base_url = api_base_url
        self._api_request_timeout_seconds = api_request_timeout_seconds

    def run(
        self,
        *,
        ibkr_account_id: str,
        market_code: str,
        scheduled_run_id: str,
    ) -> dict[str, object]:
        if (
            not self._storage_settings.enabled
            or not self._storage_settings.database_url
            or not self._storage_settings.writes_enabled
        ):
            return {
                "sent_email": False,
                "persisted_digest": False,
                "reason": "storage_unavailable",
            }
        try:
            provider = StorageConnectionProvider(
                build_database_connection_settings(
                    self._storage_settings.database_url
                )
            )
            with provider.checked_connection(require_writable=True) as checked:
                payload = self._compute_and_persist(
                    checked.connection,
                    checked.readiness,
                    ibkr_account_id=ibkr_account_id,
                    market_code=market_code,
                )
                checked.connection.commit()
        except StorageConnectionError as exc:
            logger.warning("digest runner storage error: %s", exc)
            return {
                "sent_email": False,
                "persisted_digest": False,
                "reason": "storage_connection_error",
                "detail": str(exc),
            }
        return payload

    def _compute_and_persist(
        self,
        connection: Any,
        readiness: Any,
        *,
        ibkr_account_id: str,
        market_code: str,
    ) -> dict[str, object]:
        now = self._now_provider()
        today = now.date()

        ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(connection, readiness)
        suggestion_repo = SqlAlchemyAssetSuggestionRepository(
            connection, readiness
        )
        draft_repo = SqlAlchemyAssetActionDraftRepository(connection, readiness)
        market_data_repo = SqlAlchemyMarketDataSnapshotRepository(
            connection, readiness
        )
        digest_repo = SqlAlchemyDailyDigestRepository(connection, readiness)

        latest_run = ibkr_repo.get_latest_ibkr_sync_run()
        positions: list[IbkrPositionSnapshotRecord] = []
        if latest_run is not None:
            positions = list(
                ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id)
            )

        conids = tuple({p.conid for p in positions if p.conid})
        market_snapshots: tuple[MarketDataLatestSnapshotRecord, ...] = ()
        suggestions: tuple[AssetSuggestionRecord, ...] = ()
        drafts: tuple[AssetActionDraftRecord, ...] = ()
        if conids:
            market_snapshots = (
                market_data_repo.list_latest_market_data_snapshots_by_conids(
                    conids
                ).records
            )
            suggestions = suggestion_repo.list_latest_asset_suggestions_by_conids(
                conids
            ).records
            drafts = draft_repo.list_latest_asset_action_drafts_by_conids(
                conids
            ).records

        nav_snapshots = ibkr_repo.list_ibkr_nav_snapshots_since(
            ibkr_account_id=ibkr_account_id,
            since=datetime(today.year, today.month, today.day, tzinfo=UTC)
            .replace(day=1)
            .replace(hour=0, minute=0, second=0, microsecond=0),
        )
        today_nav, prev_nav, base_currency = _resolve_nav_pair(nav_snapshots)

        positions_with_pnl = _join_positions_with_pnl(
            positions, market_snapshots
        )
        todays_drafts = _filter_today_drafts(drafts, today)

        payload = compute_daily_digest_payload(
            ibkr_account_ref=ibkr_account_id,
            market_code=market_code,
            briefing_date=today,
            generated_at=now,
            today_nav=today_nav,
            prev_nav=prev_nav,
            base_currency=base_currency,
            positions=positions_with_pnl,
            suggestions=suggestions,
            action_drafts=todays_drafts,
        )
        record = DailyDigestRecord(**payload)
        digest_repo.upsert_daily_digest(record)

        email_summary = _send_digest_email(
            digest=record,
            notifications=self._notifications,
            api_base_url=self._api_base_url,
            api_request_timeout_seconds=self._api_request_timeout_seconds,
        )

        return {
            "persisted_digest": True,
            "persisted_digest_id": record.digest_id,
            "status": record.status,
            "position_count": len(positions_with_pnl),
            "suggestion_count": len(suggestions),
            "alert_count": len(record.alerts_json or []),
            "email": email_summary,
        }


__all__ = ["DailyDigestRunner"]
