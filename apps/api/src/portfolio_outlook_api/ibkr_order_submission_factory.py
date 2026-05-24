"""Factory that picks the real ``ibapi`` order-submission client or returns
``None``.

This factory is the *single* gating point for any actual broker order
submission. Returning ``None`` means the submission endpoint must respond
with a blocked response — no fallback, no fake submission.

Locked V1 gates (every one must pass):

* ``ibkr_paper_order_submission_enabled``
* ``ibkr_paper_order_submission_real_client_enabled``
* ``ibkr_sync_account_mode == "paper"`` (paper-only locked rule)
* ``ibkr_expected_environment == "paper"``
* Host / port / client-id all set
"""

from __future__ import annotations

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_ibapi_order_submission_client import (
    IbapiOrderSubmissionClient,
    OrderSubmissionAppProtocol,
)


def build_real_order_submission_client(
    settings: Settings,
    *,
    app: OrderSubmissionAppProtocol | None = None,
) -> IbapiOrderSubmissionClient | None:
    if not settings.ibkr_paper_order_submission_enabled:
        return None
    if not settings.ibkr_paper_order_submission_real_client_enabled:
        return None
    if (settings.ibkr_sync_account_mode or "").strip().lower() != "paper":
        return None
    if (settings.ibkr_expected_environment or "").strip().lower() != "paper":
        return None
    host = settings.ibkr_paper_order_submission_host
    port = settings.ibkr_paper_order_submission_port
    client_id = settings.ibkr_paper_order_submission_client_id
    if not host or port is None or client_id is None:
        return None
    return IbapiOrderSubmissionClient(
        host=host,
        port=port,
        client_id=client_id,
        timeout_seconds=settings.ibkr_paper_order_submission_timeout_seconds,
        provider_code=settings.ibkr_paper_order_submission_provider_code,
        app=app,
    )
