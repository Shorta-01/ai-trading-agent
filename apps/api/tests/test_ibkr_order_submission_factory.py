"""Tests for the order-submission factory.

The factory is the single locked gate for any actual IBKR order. Every
gate must be enforced; tests pin each gate explicitly.
"""

from __future__ import annotations

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_ibapi_order_submission_client import (
    IbapiOrderSubmissionClient,
)
from portfolio_outlook_api.ibkr_order_submission_factory import (
    build_real_order_submission_client,
)


class _NoopApp:
    def connect(self, *_a, **_k) -> None:  # type: ignore[no-untyped-def]
        return None

    def isConnected(self) -> bool:  # noqa: N802
        return True

    def disconnect(self) -> None:
        return None

    def run(self) -> None:
        return None

    def reqIds(self, *_a, **_k) -> None:  # type: ignore[no-untyped-def] # noqa: N802
        return None

    def placeOrder(self, *_a, **_k) -> None:  # type: ignore[no-untyped-def] # noqa: N802
        return None


def _ready_settings(**overrides) -> Settings:  # type: ignore[no-untyped-def]
    values: dict[str, object] = {
        "ibkr_paper_order_submission_enabled": True,
        "ibkr_paper_order_submission_real_client_enabled": True,
        "ibkr_paper_order_submission_host": "127.0.0.1",
        "ibkr_paper_order_submission_port": 4002,
        "ibkr_paper_order_submission_client_id": 11,
        "ibkr_sync_account_mode": "paper",
        "ibkr_expected_environment": "paper",
    }
    values.update(overrides)
    return Settings(**values)


def test_factory_returns_client_when_fully_configured() -> None:
    client = build_real_order_submission_client(_ready_settings(), app=_NoopApp())
    assert isinstance(client, IbapiOrderSubmissionClient)


def test_factory_returns_none_when_submission_disabled() -> None:
    assert (
        build_real_order_submission_client(
            _ready_settings(ibkr_paper_order_submission_enabled=False), app=_NoopApp()
        )
        is None
    )


def test_factory_returns_none_when_real_client_flag_off() -> None:
    assert (
        build_real_order_submission_client(
            _ready_settings(ibkr_paper_order_submission_real_client_enabled=False),
            app=_NoopApp(),
        )
        is None
    )


def test_factory_no_longer_blocks_on_live_account_mode() -> None:
    """V1 §21.1 relock: the factory no longer rejects live mode.

    The connected IBKR account is the authority on paper vs. live, not
    an app-side `ibkr_sync_account_mode` setting. The remaining gates
    (enabled + real_client_enabled + host/port/client-id) are
    unchanged.
    """

    client = build_real_order_submission_client(
        _ready_settings(ibkr_sync_account_mode="live"), app=_NoopApp()
    )
    assert client is not None


def test_factory_no_longer_blocks_on_live_expected_environment() -> None:
    """Same relock for `ibkr_expected_environment`: a `live` value is
    informational; the factory still constructs the real client when
    the other gates pass."""

    client = build_real_order_submission_client(
        _ready_settings(ibkr_expected_environment="live"), app=_NoopApp()
    )
    assert client is not None


def test_factory_returns_none_when_host_missing() -> None:
    assert (
        build_real_order_submission_client(
            _ready_settings(ibkr_paper_order_submission_host=None), app=_NoopApp()
        )
        is None
    )


def test_factory_returns_none_when_port_missing() -> None:
    assert (
        build_real_order_submission_client(
            _ready_settings(ibkr_paper_order_submission_port=None), app=_NoopApp()
        )
        is None
    )


def test_factory_returns_none_when_client_id_missing() -> None:
    assert (
        build_real_order_submission_client(
            _ready_settings(ibkr_paper_order_submission_client_id=None), app=_NoopApp()
        )
        is None
    )
