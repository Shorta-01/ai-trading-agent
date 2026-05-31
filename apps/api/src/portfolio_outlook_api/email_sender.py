"""Operator-facing email transport.

Thin wrapper around ``smtplib`` + ``email.message.EmailMessage`` that
the notifications routes use for the "send test email" button and that
the digest runner (deferred to a follow-up) will use to deliver
end-of-day digests. Stub mode is the default: when
``settings.notifications_email_real_client_enabled`` is False the
sender logs the email payload instead of opening an SMTP session, so a
fresh deploy with no SMTP creds doesn't crash on first save.

Doctrine: this module never reaches into storage; every input is a
plain value the caller resolves. Keeps the test surface small.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SmtpTransportConfig:
    """Plain-value SMTP creds. ``password`` is optional so a relay that
    accepts unauthenticated submission still works."""

    host: str
    port: int
    username: str | None
    password: str | None
    from_address: str
    to_address: str
    use_tls: bool


@dataclass(frozen=True)
class EmailSendResult:
    sent: bool
    status: str  # "sent" | "stubbed" | "smtp_error" | "config_missing"
    detail_nl: str
    used_host: str | None = None


def _build_message(
    *,
    config: SmtpTransportConfig,
    subject: str,
    body_plain: str,
    body_html: str | None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.from_address
    msg["To"] = config.to_address
    msg.set_content(body_plain)
    if body_html:
        # `add_alternative` upgrades the message to multipart/alternative
        # so HTML-capable clients render the styled version while
        # plain-text clients keep the fallback.
        msg.add_alternative(body_html, subtype="html")
    return msg


def send_email(
    *,
    config: SmtpTransportConfig | None,
    subject: str,
    body_plain: str,
    body_html: str | None = None,
    real_client_enabled: bool = False,
) -> EmailSendResult:
    """Send one operator-facing email.

    Returns a structured result so the caller can audit the outcome
    without needing to catch SMTP exceptions itself. The boolean
    ``real_client_enabled`` gate keeps a fresh deploy in stub mode
    until the operator explicitly opts into outbound SMTP.
    """

    if config is None:
        return EmailSendResult(
            sent=False,
            status="config_missing",
            detail_nl="SMTP-instellingen ontbreken; e-mail niet verzonden.",
        )
    if not real_client_enabled:
        logger.info(
            "Email stub: to=%s subject=%r (real client disabled)",
            config.to_address,
            subject,
        )
        return EmailSendResult(
            sent=False,
            status="stubbed",
            detail_nl=(
                "Stub-modus: e-mail is opgesteld maar niet verzonden. "
                "Zet de real-client flag aan om SMTP daadwerkelijk te gebruiken."
            ),
            used_host=config.host,
        )

    message = _build_message(
        config=config,
        subject=subject,
        body_plain=body_plain,
        body_html=body_html,
    )
    try:
        smtp_cls = smtplib.SMTP_SSL if config.use_tls and config.port == 465 else smtplib.SMTP
        with smtp_cls(config.host, config.port, timeout=10) as smtp:
            if config.use_tls and config.port != 465:
                smtp.starttls()
            if config.username and config.password:
                smtp.login(config.username, config.password)
            smtp.send_message(message)
    except smtplib.SMTPException as exc:
        logger.warning("SMTP send failed: %s", exc)
        return EmailSendResult(
            sent=False,
            status="smtp_error",
            detail_nl=f"SMTP-fout: {exc}",
            used_host=config.host,
        )
    except OSError as exc:
        # Catches network-level failures (DNS, refused, timeout).
        logger.warning("SMTP transport failed: %s", exc)
        return EmailSendResult(
            sent=False,
            status="smtp_error",
            detail_nl=f"Netwerkfout naar SMTP: {exc}",
            used_host=config.host,
        )

    logger.info(
        "Email sent: to=%s subject=%r via %s",
        config.to_address,
        subject,
        config.host,
    )
    return EmailSendResult(
        sent=True,
        status="sent",
        detail_nl="E-mail succesvol verzonden.",
        used_host=config.host,
    )


__all__ = [
    "EmailSendResult",
    "SmtpTransportConfig",
    "send_email",
]
