"""Factory that picks the real ibapi sync adapter or returns ``None``.

The factory is the single point that decides between the disabled-by-default
in-memory ``NotConfiguredIbkrAdapter`` (used when nothing is set up) and the
real ``IbapiReadOnlySyncClient`` (used when the operator has explicitly enabled
real read-only sync and provided host/port/client-id).

Returning ``None`` instead of an empty adapter lets the orchestrator distinguish
"no real client configured" from "real client configured but produced no rows",
which matters for status messages and Prediction Diary reasoning later.
"""

from __future__ import annotations

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_ibapi_sync_client import (
    IbapiReadOnlySyncClient,
    IbapiSyncAppProtocol,
)
from portfolio_outlook_api.ibkr_sync_contracts import IbkrReadOnlyAdapter


def build_real_sync_adapter(
    settings: Settings,
    *,
    app: IbapiSyncAppProtocol | None = None,
) -> IbkrReadOnlyAdapter | None:
    """Return a real read-only sync adapter when configured, otherwise ``None``.

    Gating (V1.2 §BZ — geen software-side mode-blok meer):

    * ``ibkr_sync_real_client_enabled`` must be True.
    * ``ibkr_sync_enabled`` must be True.
    * ``ibkr_sync_readonly`` must remain True.
    * Host / port / client-id must all be configured.

    De ``ibkr_sync_account_mode`` setting is informatief — de IBKR
    account-id prefix bepaalt of er paper- of live-orders worden
    geplaatst, niet een software-side gate.

    Optional ``app`` parameter lets tests inject a fake ibapi application so the
    real-adapter path can be exercised in CI without a TWS/Gateway.
    """

    if not settings.ibkr_sync_real_client_enabled:
        return None
    if not settings.ibkr_sync_enabled:
        return None
    if not settings.ibkr_sync_readonly:
        return None
    host = settings.ibkr_sync_host
    port = settings.ibkr_sync_port
    client_id = settings.ibkr_sync_client_id
    if host is None or port is None or client_id is None:
        return None
    return IbapiReadOnlySyncClient(
        host=host,
        port=port,
        client_id=client_id,
        timeout_seconds=settings.ibkr_sync_timeout_seconds,
        account_summary_tags=settings.ibkr_sync_account_summary_tags,
        provider_code=settings.ibkr_sync_provider_code,
        app=app,
    )
