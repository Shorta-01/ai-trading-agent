"""Worker-side SMTP email sender (mirror of the API's).

Duplicated by design: apps/api and apps/worker are deployed
independently and importing across that boundary risks accidentally
coupling them in CI. Keep the two copies in sync — a parity test in
``tests/test_email_sender.py`` asserts the public surface matches.

Same contract as ``apps/api/.../email_sender.py``: stub mode is the
default. The worker only opens an SMTP session when
``settings.notifications.real_client_enabled`` is True.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SmtpTransportConfig:
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
        smtp_cls = (
            smtplib.SMTP_SSL
            if config.use_tls and config.port == 465
            else smtplib.SMTP
        )
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
