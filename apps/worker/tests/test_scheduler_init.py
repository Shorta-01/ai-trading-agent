"""Task 127 — :class:`PortfolioScheduler` start/stop + job-registration tests.

Storage and the IBKR gateway are injected as fakes; APScheduler runs
fully in-process with a memory job store so no live Postgres is
required. The tests exercise:

* The two locked cron triggers (06:00 + hourly 07:00-21:00) are
  registered.
* The ``WORKER_SCHEDULER__ENABLED=false`` default keeps the worker
  from starting any jobs.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from portfolio_outlook_worker.config import (
    IbkrSettings,
    SchedulerSettings,
    StorageSettings,
)
from portfolio_outlook_worker.ibkr_gateway import IbkrGateway
from portfolio_outlook_worker.scheduler import (
    _CANCEL_SWEEP_JOB_ID,
    _MARKET_CLOSE_JOB_PREFIX,
    _PRE_BRIEFING_JOB_ID,
    _SUBMISSION_SWEEP_JOB_ID,
    PortfolioScheduler,
)


def _build_with_sweeps(
    *, order_adapter: object | None, ibkr_settings: IbkrSettings
) -> PortfolioScheduler:
    return PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=ibkr_settings,
        scheduler_settings=SchedulerSettings(
            enabled=True, timezone="Europe/Brussels", heartbeat_interval_seconds=60
        ),
        worker_id="worker-test",
        scheduler_factory=_scheduler_factory,
        order_adapter=order_adapter,
    )


def test_order_sweeps_not_registered_by_default() -> None:
    scheduler = _build()  # no order adapter -> no order jobs
    try:
        scheduler.start()
        assert scheduler._scheduler.get_job(_SUBMISSION_SWEEP_JOB_ID) is None
        assert scheduler._scheduler.get_job(_CANCEL_SWEEP_JOB_ID) is None
    finally:
        scheduler.stop()


def test_submission_sweep_registered_when_enabled_with_adapter() -> None:
    scheduler = _build_with_sweeps(
        order_adapter=object(),
        ibkr_settings=IbkrSettings(
            account_id="DU1234567", submission_sweep_enabled=True
        ),
    )
    try:
        scheduler.start()
        assert scheduler._scheduler.get_job(_SUBMISSION_SWEEP_JOB_ID) is not None
        assert scheduler._scheduler.get_job(_CANCEL_SWEEP_JOB_ID) is None
    finally:
        scheduler.stop()


def test_cancel_sweep_registered_when_enabled_with_adapter() -> None:
    scheduler = _build_with_sweeps(
        order_adapter=object(),
        ibkr_settings=IbkrSettings(account_id="DU1234567", cancel_sweep_enabled=True),
    )
    try:
        scheduler.start()
        assert scheduler._scheduler.get_job(_CANCEL_SWEEP_JOB_ID) is not None
    finally:
        scheduler.stop()


def test_sweeps_not_registered_without_adapter_even_if_enabled() -> None:
    scheduler = _build_with_sweeps(
        order_adapter=None,
        ibkr_settings=IbkrSettings(
            account_id="DU1234567", submission_sweep_enabled=True
        ),
    )
    try:
        scheduler.start()
        assert scheduler._scheduler.get_job(_SUBMISSION_SWEEP_JOB_ID) is None
    finally:
        scheduler.stop()


class _StubGateway:
    def is_connected(self) -> bool:
        return False


def _scheduler_factory(*, database_url, timezone):  # type: ignore[no-untyped-def]  # noqa: ARG001
    # Memory-backed scheduler so tests never touch storage.
    return BackgroundScheduler(timezone=timezone)


def _build(*, scheduler_enabled: bool = True) -> PortfolioScheduler:
    return PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(),
        scheduler_settings=SchedulerSettings(
            enabled=scheduler_enabled,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test",
        scheduler_factory=_scheduler_factory,
    )


def test_start_registers_pre_briefing_job_with_06_00_cron() -> None:
    scheduler = _build()
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job(_PRE_BRIEFING_JOB_ID)
        assert job is not None
        cron_repr = repr(job.trigger)
        assert "hour='6'" in cron_repr
        assert "minute='0'" in cron_repr
        assert "Europe/Brussels" in cron_repr
    finally:
        scheduler.stop()


def test_legacy_hourly_job_is_no_longer_registered() -> None:
    """The naive ``hour="7-21"`` hourly fire is gone — replaced by the
    market-aware scheduler (per-followed-market open / close fires).
    With no markets selected, no market fires register either."""

    scheduler = _build()
    try:
        scheduler.start()
        # No legacy ``hourly`` job lives in the scheduler anymore.
        assert scheduler._scheduler.get_job("hourly") is None
        # And with no universe selected we register zero market fires.
        market_jobs = [
            j
            for j in scheduler._scheduler.get_jobs()
            if j.id.startswith(_MARKET_CLOSE_JOB_PREFIX)
        ]
        assert market_jobs == []
    finally:
        scheduler.stop()


def test_market_close_fires_registered_for_selected_universe() -> None:
    """When the operator picks BEL20 + AEX + DAX40, register two
    close fires (Euronext + Xetra) on weekdays only, in the right
    timezones."""

    scheduler = PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
            universe_scan_index_codes="BEL20,AEX,DAX40",
            per_market_close_digest_enabled=True,
            per_market_open_alerts_enabled=False,
        ),
        worker_id="worker-test-markets",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        euronext = scheduler._scheduler.get_job(
            f"{_MARKET_CLOSE_JOB_PREFIX}EURONEXT"
        )
        xetra = scheduler._scheduler.get_job(
            f"{_MARKET_CLOSE_JOB_PREFIX}XETRA"
        )
        assert euronext is not None
        assert xetra is not None
        cron_repr = repr(euronext.trigger)
        # +15min buffer past the 17:30 Euronext close → 17:45.
        assert "hour='17'" in cron_repr
        assert "minute='45'" in cron_repr
        assert "Europe/Brussels" in cron_repr
        # Weekday-only — explicit ``day_of_week=mon-fri``.
        assert "day_of_week='mon-fri'" in cron_repr
    finally:
        scheduler.stop()


def test_start_is_idempotent() -> None:
    scheduler = _build()
    try:
        scheduler.start()
        scheduler.start()  # second call is a no-op
        assert scheduler._scheduler.get_job(_PRE_BRIEFING_JOB_ID) is not None
    finally:
        scheduler.stop()


def test_stop_is_idempotent_and_safe_before_start() -> None:
    scheduler = _build()
    scheduler.stop()  # no error when never started
    scheduler.start()
    scheduler.stop()
    scheduler.stop()  # second stop is a no-op


def test_worker_id_is_stable_across_lifecycle() -> None:
    scheduler = _build()
    assert scheduler.worker_id == "worker-test"
    scheduler.start()
    assert scheduler.worker_id == "worker-test"
    scheduler.stop()


def test_next_runs_lists_both_jobs_after_start() -> None:
    scheduler = _build()
    try:
        scheduler.start()
        runs = scheduler.next_runs()
        # Memory-backed scheduler returns next_run_time only after the
        # first tick; with no fires yet, APScheduler still populates
        # the trigger so next_run_time is set immediately.
        # Sinds 2026-06-16 staan default-aan: reconciliation_sweep
        # (§BZ audit-cleanup) en sell_signal_sweep (§CB.1 — CLAUDE.md
        # §11 "SELL-monitoring blijft draaien"). Plus heartbeat +
        # pre_briefing = 4 jobs.
        assert len(runs) == 4
    finally:
        scheduler.stop()


def test_next_runs_empty_when_scheduler_not_started() -> None:
    scheduler = _build()
    assert scheduler.next_runs() == []


# ---- explicit job guards (max_instances / coalesce / misfire_grace_time)
#      + jitter + configurable sweep interval -----------------------------


def _assert_explicit_guards(job) -> None:  # type: ignore[no-untyped-def]
    """Every job registered by the worker scheduler must explicitly
    set the single-instance + coalesce + misfire guards rather than
    relying on APScheduler's defaults."""

    assert job.max_instances == 1, f"{job.id} should pin max_instances=1"
    assert job.coalesce is True, f"{job.id} should set coalesce=True"
    assert job.misfire_grace_time is not None and job.misfire_grace_time > 0, (
        f"{job.id} should set misfire_grace_time"
    )


def test_cron_jobs_have_explicit_guards() -> None:
    scheduler = PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
            # Force the market-close fire to register so we can assert
            # its guards alongside pre-briefing.
            universe_scan_index_codes="BEL20",
            per_market_close_digest_enabled=True,
        ),
        worker_id="worker-test-guards",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        _assert_explicit_guards(scheduler._scheduler.get_job(_PRE_BRIEFING_JOB_ID))
        _assert_explicit_guards(
            scheduler._scheduler.get_job(f"{_MARKET_CLOSE_JOB_PREFIX}EURONEXT")
        )
    finally:
        scheduler.stop()


def test_heartbeat_job_has_explicit_guards_and_jitter() -> None:
    scheduler = _build()
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job("heartbeat")
        assert job is not None
        _assert_explicit_guards(job)
        assert getattr(job.trigger, "jitter", None) is not None, (
            "heartbeat interval should carry jitter so multi-replica deploys "
            "don't fire in lockstep"
        )
    finally:
        scheduler.stop()


# ---- IBKR auto-reconnect heartbeat (V1.2 §BY / GAPS.md P2-1) -------


class _ReconnectGateway:
    """Test-double dat een connectie-cycle (verbroken → connect) modelt."""

    def __init__(self, *, connected: bool = False) -> None:
        self._connected = connected
        self.connect_calls: list[dict] = []
        self.connect_result = type(
            "_Result",
            (),
            {"connected": True, "error_nl": None, "account_mode": "paper"},
        )()

    def is_connected(self) -> bool:
        return self._connected

    def connect(
        self, *, host: str, port: int, client_id: int, account_id: str
    ):
        self.connect_calls.append(
            {
                "host": host,
                "port": port,
                "client_id": client_id,
                "account_id": account_id,
            }
        )
        # The connect succeeds on first attempt so the test sees the
        # transition is_connected: False → True.
        self._connected = self.connect_result.connected
        return self.connect_result


def test_auto_reconnect_disabled_by_default() -> None:
    """Default ``ibkr_auto_reconnect_enabled=False`` betekent: nooit
    reconnect-call, ook niet als reconciler-gateway disconnect't."""

    reconciler_gateway = _ReconnectGateway(connected=False)
    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        reconciler_gateway=reconciler_gateway,
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True, account_id="DU1234567"
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-no-reconnect",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        scheduler._maybe_reconnect_ibkr_gateway()
        assert reconciler_gateway.connect_calls == []
    finally:
        scheduler.stop()


def test_auto_reconnect_skips_when_already_connected() -> None:
    """Wanneer auto-reconnect aanstaat maar de reconciler-gateway
    verbonden is, geen connect-call (idempotent + zuinig)."""

    reconciler_gateway = _ReconnectGateway(connected=True)
    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        reconciler_gateway=reconciler_gateway,
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True,
            account_id="DU1234567",
            ibkr_auto_reconnect_enabled=True,
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-reconnect-already-up",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        scheduler._maybe_reconnect_ibkr_gateway()
        assert reconciler_gateway.connect_calls == []
    finally:
        scheduler.stop()


def test_auto_reconnect_fires_when_gateway_disconnected() -> None:
    """V1.2 §BY — auto-reconnect aan + reconciler-gateway disconnected
    → één connect-call met host/port/account_id en
    ``reconciler_session_client_id`` (NIET de boot-test client_id)."""

    reconciler_gateway = _ReconnectGateway(connected=False)
    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        reconciler_gateway=reconciler_gateway,
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True,
            host="127.0.0.1",
            port=7497,
            client_id=1,
            reconciler_session_client_id=3,
            account_id="DU1234567",
            ibkr_auto_reconnect_enabled=True,
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-reconnect-down",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        scheduler._maybe_reconnect_ibkr_gateway()
        assert len(reconciler_gateway.connect_calls) == 1
        assert reconciler_gateway.connect_calls[0] == {
            "host": "127.0.0.1",
            "port": 7497,
            "client_id": 3,
            "account_id": "DU1234567",
        }
        # The mock flipped to connected=True, mirroring SDK behaviour.
        assert reconciler_gateway.is_connected() is True
    finally:
        scheduler.stop()


def test_auto_reconnect_skips_without_account_id() -> None:
    """Geen ``account_id`` → reconnect is een no-op, geen exception."""

    reconciler_gateway = _ReconnectGateway(connected=False)
    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        reconciler_gateway=reconciler_gateway,
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True,
            ibkr_auto_reconnect_enabled=True,
            # account_id intentionally left None
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-reconnect-no-account",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        scheduler._maybe_reconnect_ibkr_gateway()
        assert reconciler_gateway.connect_calls == []
    finally:
        scheduler.stop()


def test_auto_reconnect_skips_when_no_reconciler_gateway() -> None:
    """V1.2 §BM-2 + §BY interplay: wanneer er geen
    ``reconciler_gateway`` is geinjecteerd (reconciliation cron uit)
    moet de heartbeat een no-op zijn — de hoofdgateway is een
    disconnected boot-stub en mag NIET geraakt worden."""

    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        # No reconciler_gateway — production-pad wanneer cron uit staat.
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True,
            account_id="DU1234567",
            ibkr_auto_reconnect_enabled=True,
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-reconnect-no-reconciler",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        # Should not raise even though gateway has no .connect.
        scheduler._maybe_reconnect_ibkr_gateway()
    finally:
        scheduler.stop()


def test_auto_reconnect_swallows_connect_exception() -> None:
    """Een raise tijdens connect mag de scheduler-loop niet crashen."""

    class _BadGateway:
        def is_connected(self) -> bool:
            return False

        def connect(self, **_kwargs):
            raise RuntimeError("TWS unreachable")

    bad_gateway = _BadGateway()
    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        reconciler_gateway=bad_gateway,
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True,
            account_id="DU1234567",
            ibkr_auto_reconnect_enabled=True,
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-reconnect-raise",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        # Should NOT raise.
        scheduler._maybe_reconnect_ibkr_gateway()
    finally:
        scheduler.stop()


class _ReconnectingOrderAdapter:
    """Test stub voor de §BZ-follow-up order-adapter heartbeat."""

    def __init__(self, *, connected: bool) -> None:
        self._connected = connected
        self.reconnect_calls = 0

    def is_connected(self) -> bool:
        return self._connected

    def reconnect(self) -> bool:
        self.reconnect_calls += 1
        self._connected = True
        return True


def test_order_adapter_reconnect_fires_when_disconnected() -> None:
    """V1.2 §BZ follow-up: heartbeat heropent ook de order-sessie
    wanneer die dropt — niet alleen het reconciler-gateway."""

    adapter = _ReconnectingOrderAdapter(connected=False)
    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        order_adapter=adapter,
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True,
            account_id="DU1234567",
            ibkr_auto_reconnect_enabled=True,
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-order-reconnect",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        scheduler._maybe_reconnect_order_adapter()
        assert adapter.reconnect_calls == 1
        assert adapter.is_connected() is True
        # Second tick: already connected → no-op.
        scheduler._maybe_reconnect_order_adapter()
        assert adapter.reconnect_calls == 1
    finally:
        scheduler.stop()


def test_order_adapter_reconnect_skips_when_flag_off() -> None:
    """Default ``ibkr_auto_reconnect_enabled=False`` betekent: nooit
    reconnect-call op de order-adapter."""

    adapter = _ReconnectingOrderAdapter(connected=False)
    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        order_adapter=adapter,
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True,
            account_id="DU1234567",
            # auto_reconnect default False
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-order-reconnect-off",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        scheduler._maybe_reconnect_order_adapter()
        assert adapter.reconnect_calls == 0
    finally:
        scheduler.stop()


def test_sighup_runtime_config_reload_re_overlays_account_id(monkeypatch) -> None:
    """V1.2 §BZ vervolg — SIGHUP zet flag; heartbeat hook leest
    runtime_config opnieuw en swap't ``settings.ibkr.account_id``."""

    from portfolio_outlook_worker import runtime_config_overlay

    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True, account_id="DU1111111"
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-sighup",
        scheduler_factory=_scheduler_factory,
    )
    # Mock de overlay zodat 'm de account_id naar DU2222222 wijzigt.
    overlay_called: list[bool] = []

    def _fake_overlay(settings_obj):
        overlay_called.append(True)
        settings_obj.ibkr.account_id = "DU2222222"

    monkeypatch.setattr(
        runtime_config_overlay,
        "apply_worker_runtime_config_overlay",
        _fake_overlay,
    )
    try:
        scheduler.start()
        # Zonder flag: geen overlay-call.
        scheduler._maybe_reload_runtime_config()
        assert overlay_called == []
        # Met flag: één overlay-call + scheduler's ibkr_settings is bijgewerkt.
        scheduler._runtime_config_reload_requested = True
        scheduler._maybe_reload_runtime_config()
        assert overlay_called == [True]
        assert scheduler._ibkr_settings.account_id == "DU2222222"
        # Flag wordt direct gereset zodat een herhaalde fout niet
        # elke heartbeat opnieuw probeert.
        assert (
            getattr(scheduler, "_runtime_config_reload_requested", False)
            is False
        )
    finally:
        scheduler.stop()


def test_reload_writes_runtime_config_reloaded_system_event(monkeypatch) -> None:
    """V1.2 §BZ vervolg — bij een succesvolle reload met
    daadwerkelijke account-id wijziging MOET een SystemEvent worden
    geschreven zodat de operator visueel bevestiging krijgt op
    /portefeuille dat de auto-reload werkte."""

    from portfolio_outlook_worker import error_capture, runtime_config_overlay

    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True, account_id="DU1111111"
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-reload-event",
        scheduler_factory=_scheduler_factory,
    )

    def _fake_overlay(settings_obj):
        settings_obj.ibkr.account_id = "U7654321"  # paper → live wissel

    monkeypatch.setattr(
        runtime_config_overlay,
        "apply_worker_runtime_config_overlay",
        _fake_overlay,
    )
    captured: list[dict[str, object]] = []
    monkeypatch.setattr(
        error_capture,
        "record_worker_event",
        lambda **kwargs: captured.append(kwargs),
    )

    try:
        scheduler.start()
        scheduler._runtime_config_reload_requested = True
        scheduler._maybe_reload_runtime_config()
        assert len(captured) == 1
        evt = captured[0]
        assert evt["event_code"] == "runtime_config_reloaded"
        assert evt["category"] == "ibkr_config_change"
        assert evt["severity"] == "info"
        # Bevat zowel oude als nieuwe account-id zodat operator ziet
        # dat de wijziging correct is opgepikt.
        assert "DU1111111" in evt["message_nl"]
        assert "U7654321" in evt["message_nl"]
    finally:
        scheduler.stop()


def test_reload_does_not_write_event_when_account_id_unchanged(
    monkeypatch,
) -> None:
    """Wanneer de overlay het account-id ongewijzigd laat (b.v. operator
    save't dezelfde waarde), MOETEN we geen lege SystemEvent schrijven —
    anders krijgt operator nuttig-loos noise op /portefeuille."""

    from portfolio_outlook_worker import error_capture, runtime_config_overlay

    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True, account_id="DU1111111"
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-reload-noop",
        scheduler_factory=_scheduler_factory,
    )

    def _fake_overlay(settings_obj):
        # Operator save't dezelfde waarde als voorheen → geen wijziging.
        settings_obj.ibkr.account_id = "DU1111111"

    monkeypatch.setattr(
        runtime_config_overlay,
        "apply_worker_runtime_config_overlay",
        _fake_overlay,
    )
    captured: list[dict[str, object]] = []
    monkeypatch.setattr(
        error_capture,
        "record_worker_event",
        lambda **kwargs: captured.append(kwargs),
    )

    try:
        scheduler.start()
        scheduler._runtime_config_reload_requested = True
        scheduler._maybe_reload_runtime_config()
        assert captured == []
    finally:
        scheduler.stop()


def test_reload_disconnects_reconciler_and_order_session_on_account_change(
    monkeypatch,
) -> None:
    """V1.2 §BZ vervolg — proactive disconnect: na een account-id
    wijziging moeten ``_reconciler_gateway`` en ``_order_adapter``
    worden disconnected zodat de §BY reconnect-heartbeat ze
    re-establishet tegen het nieuwe account."""

    from portfolio_outlook_worker import runtime_config_overlay

    reconciler_disconnect_calls: list[bool] = []
    order_disconnect_calls: list[bool] = []

    class _FakeGateway:
        def is_connected(self) -> bool:
            return True

        def disconnect(self) -> None:
            reconciler_disconnect_calls.append(True)

    class _FakeIB:
        def disconnect(self) -> None:
            order_disconnect_calls.append(True)

    class _FakeOrderAdapter:
        def __init__(self) -> None:
            self._ib = _FakeIB()

        def is_connected(self) -> bool:
            return True

    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        reconciler_gateway=_FakeGateway(),
        order_adapter=_FakeOrderAdapter(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True, account_id="DU1111111"
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-disconnect-on-reload",
        scheduler_factory=_scheduler_factory,
    )

    def _fake_overlay(settings_obj):
        settings_obj.ibkr.account_id = "U7654321"

    monkeypatch.setattr(
        runtime_config_overlay,
        "apply_worker_runtime_config_overlay",
        _fake_overlay,
    )

    try:
        scheduler.start()
        scheduler._runtime_config_reload_requested = True
        scheduler._maybe_reload_runtime_config()
        assert reconciler_disconnect_calls == [True]
        assert order_disconnect_calls == [True]
    finally:
        scheduler.stop()


def test_reload_does_not_disconnect_when_account_id_unchanged(
    monkeypatch,
) -> None:
    """Operator save't dezelfde waarde → geen disconnect, anders
    zou elke save nodeloze TWS-reconnects veroorzaken."""

    from portfolio_outlook_worker import runtime_config_overlay

    reconciler_disconnect_calls: list[bool] = []

    class _FakeGateway:
        def is_connected(self) -> bool:
            return True

        def disconnect(self) -> None:
            reconciler_disconnect_calls.append(True)

    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        reconciler_gateway=_FakeGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(
            enabled=True, account_id="DU1111111"
        ),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-no-disconnect",
        scheduler_factory=_scheduler_factory,
    )

    def _fake_overlay(settings_obj):
        settings_obj.ibkr.account_id = "DU1111111"  # zelfde waarde

    monkeypatch.setattr(
        runtime_config_overlay,
        "apply_worker_runtime_config_overlay",
        _fake_overlay,
    )

    try:
        scheduler.start()
        scheduler._runtime_config_reload_requested = True
        scheduler._maybe_reload_runtime_config()
        assert reconciler_disconnect_calls == []
    finally:
        scheduler.stop()


def test_sighup_runtime_config_reload_swallows_exceptions(monkeypatch) -> None:
    """Een crash in de overlay mag de scheduler-loop niet kapot maken."""

    from portfolio_outlook_worker import runtime_config_overlay

    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(enabled=True, account_id="DU1111111"),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-sighup-raise",
        scheduler_factory=_scheduler_factory,
    )

    def _bad_overlay(_settings_obj):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        runtime_config_overlay,
        "apply_worker_runtime_config_overlay",
        _bad_overlay,
    )
    try:
        scheduler.start()
        scheduler._runtime_config_reload_requested = True
        # Should NOT raise.
        scheduler._maybe_reload_runtime_config()
        # Flag is reset zelfs bij fout.
        assert (
            getattr(scheduler, "_runtime_config_reload_requested", False)
            is False
        )
    finally:
        scheduler.stop()


def test_reload_writes_runtime_config_reload_failed_event_on_exception(
    monkeypatch,
) -> None:
    """V1.2 §BZ vervolg — wanneer de overlay raise't, MOET er een
    ``runtime_config_reload_failed`` SystemEvent worden geschreven
    zodat de operator op /portefeuille ziet dat de auto-reload
    faalde i.p.v. stil een lege response te krijgen."""

    from portfolio_outlook_worker import error_capture, runtime_config_overlay

    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(enabled=True, account_id="DU1111111"),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-reload-failed-event",
        scheduler_factory=_scheduler_factory,
    )

    def _bad_overlay(_settings_obj):
        raise RuntimeError("simulated overlay failure")

    monkeypatch.setattr(
        runtime_config_overlay,
        "apply_worker_runtime_config_overlay",
        _bad_overlay,
    )
    captured: list[dict[str, object]] = []
    monkeypatch.setattr(
        error_capture,
        "record_worker_event",
        lambda **kwargs: captured.append(kwargs),
    )

    try:
        scheduler.start()
        scheduler._runtime_config_reload_requested = True
        # Mag niet raise't.
        scheduler._maybe_reload_runtime_config()
        # Er moet precies één error-event geschreven zijn.
        assert len(captured) == 1
        evt = captured[0]
        assert evt["event_code"] == "runtime_config_reload_failed"
        assert evt["severity"] == "error"
        assert evt["category"] == "ibkr_config_change"
        # Technische details bevatten de exception-class.
        assert "RuntimeError" in evt["message_nl"]
        assert "simulated overlay failure" in evt["technical_summary"]
    finally:
        scheduler.stop()


def test_reload_failed_event_swallows_record_worker_event_crash(
    monkeypatch,
) -> None:
    """Defensief: zelfs als ``record_worker_event`` zelf raise't,
    mag de scheduler-loop niet crashen. Anders zou een storage-fout
    de hele heartbeat killing."""

    from portfolio_outlook_worker import error_capture, runtime_config_overlay

    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(enabled=True, account_id="DU1111111"),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-double-failure",
        scheduler_factory=_scheduler_factory,
    )

    def _bad_overlay(_settings_obj):
        raise RuntimeError("first failure")

    def _bad_recorder(**_kwargs):
        raise RuntimeError("second failure (storage)")

    monkeypatch.setattr(
        runtime_config_overlay,
        "apply_worker_runtime_config_overlay",
        _bad_overlay,
    )
    monkeypatch.setattr(
        error_capture,
        "record_worker_event",
        _bad_recorder,
    )

    try:
        scheduler.start()
        scheduler._runtime_config_reload_requested = True
        # Should NOT raise — zelfs niet als zowel overlay als event-
        # recorder crashen.
        scheduler._maybe_reload_runtime_config()
    finally:
        scheduler.stop()


def test_poll_runtime_config_changed_returns_true_when_updated_at_advances() -> None:
    """V1.2 §BZ vervolg — auto-poll bemerkt een DB-update zonder
    SIGHUP nodig te hebben."""

    from datetime import UTC, datetime

    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        storage_settings=StorageSettings(
            enabled=True,
            database_url="postgresql://fake",
            writes_enabled=True,
        ),
        ibkr_settings=IbkrSettings(enabled=True, account_id="DU1111111"),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-poll",
        scheduler_factory=_scheduler_factory,
    )

    class _FakeRecord:
        def __init__(self, updated_at):
            self.updated_at = updated_at

    times = iter(
        [
            datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),
            datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),  # zelfde
            datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC),  # nieuwer
        ]
    )

    # Stub de storage helper i.p.v. echte DB-connectie te mocken.
    # Direct op de instance — geen scheduler.start() nodig (die zou
    # de echte storage proberen te raken voor het heartbeat-audit).
    scheduler._fetch_runtime_config_record = lambda: _FakeRecord(next(times))  # type: ignore[method-assign]

    # Eerste poll = cold-start markering, geen reload.
    assert scheduler._poll_runtime_config_changed() is False
    # Tweede poll = zelfde updated_at, geen reload.
    assert scheduler._poll_runtime_config_changed() is False
    # Derde poll = nieuwere updated_at, MOET reload triggeren.
    assert scheduler._poll_runtime_config_changed() is True


def test_poll_runtime_config_changed_returns_false_when_storage_disabled() -> None:
    scheduler = PortfolioScheduler(
        gateway=IbkrGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(enabled=True, account_id="DU1111111"),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test-poll-off",
        scheduler_factory=_scheduler_factory,
    )
    try:
        scheduler.start()
        # Storage uit → poll is een no-op.
        assert scheduler._poll_runtime_config_changed() is False
    finally:
        scheduler.stop()


def test_submission_sweep_honors_configurable_interval_and_jitter() -> None:
    scheduler = _build_with_sweeps(
        order_adapter=object(),
        ibkr_settings=IbkrSettings(
            account_id="DU1234567",
            submission_sweep_enabled=True,
            sweep_interval_seconds=45,
        ),
    )
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job(_SUBMISSION_SWEEP_JOB_ID)
        assert job is not None
        _assert_explicit_guards(job)
        # IntervalTrigger.interval is a timedelta in seconds.
        assert int(job.trigger.interval.total_seconds()) == 45
        assert getattr(job.trigger, "jitter", None) is not None
    finally:
        scheduler.stop()


def test_cancel_sweep_honors_configurable_interval_and_jitter() -> None:
    scheduler = _build_with_sweeps(
        order_adapter=object(),
        ibkr_settings=IbkrSettings(
            account_id="DU1234567",
            cancel_sweep_enabled=True,
            sweep_interval_seconds=30,
        ),
    )
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job(_CANCEL_SWEEP_JOB_ID)
        assert job is not None
        _assert_explicit_guards(job)
        assert int(job.trigger.interval.total_seconds()) == 30
        assert getattr(job.trigger, "jitter", None) is not None
    finally:
        scheduler.stop()


# ---- #1 + #2 API-trigger jobs (worker owns scheduling) ------------------


def _build_with_api_triggers(
    *,
    morning_chain_trigger_enabled: bool = False,
    morning_chain_after_pre_briefing: bool = False,
    ibkr_sync_trigger_enabled: bool = False,
    ibkr_sync_interval_minutes: int = 15,
    api_base_url: str | None = "http://api:8000",
) -> PortfolioScheduler:
    return PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
            api_base_url=api_base_url,
            morning_chain_trigger_enabled=morning_chain_trigger_enabled,
            morning_chain_after_pre_briefing=morning_chain_after_pre_briefing,
            ibkr_sync_trigger_enabled=ibkr_sync_trigger_enabled,
            ibkr_sync_interval_minutes=ibkr_sync_interval_minutes,
        ),
        worker_id="worker-test",
        scheduler_factory=_scheduler_factory,
    )


def test_morning_chain_trigger_job_not_registered_by_default() -> None:
    scheduler = _build_with_api_triggers()
    try:
        scheduler.start()
        assert scheduler._scheduler.get_job("morning_chain_trigger") is None
        assert scheduler._scheduler.get_job("ibkr_sync_trigger") is None
    finally:
        scheduler.stop()


def test_morning_chain_trigger_job_registered_when_enabled() -> None:
    scheduler = _build_with_api_triggers(morning_chain_trigger_enabled=True)
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job("morning_chain_trigger")
        assert job is not None
        assert job.max_instances == 1
        assert job.coalesce is True
    finally:
        scheduler.stop()


def test_morning_chain_trigger_job_skipped_when_signal_chain_takes_over() -> None:
    """When pre-briefing tail-call is configured the standalone cron
    is intentionally NOT registered — avoiding a double fire."""

    scheduler = _build_with_api_triggers(
        morning_chain_trigger_enabled=True,
        morning_chain_after_pre_briefing=True,
    )
    try:
        scheduler.start()
        assert scheduler._scheduler.get_job("morning_chain_trigger") is None
    finally:
        scheduler.stop()


def test_ibkr_sync_trigger_job_registered_with_interval_and_jitter() -> None:
    scheduler = _build_with_api_triggers(
        ibkr_sync_trigger_enabled=True, ibkr_sync_interval_minutes=5
    )
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job("ibkr_sync_trigger")
        assert job is not None
        assert int(job.trigger.interval.total_seconds()) == 5 * 60
        assert getattr(job.trigger, "jitter", None) is not None
    finally:
        scheduler.stop()


def _build_with_explanation_batch_trigger(
    *,
    morning_explanation_batch_trigger_enabled: bool = False,
    morning_explanation_batch_cron: str = "45 6 * * *",
    api_base_url: str | None = "http://api:8000",
) -> PortfolioScheduler:
    return PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
            api_base_url=api_base_url,
            morning_explanation_batch_trigger_enabled=(
                morning_explanation_batch_trigger_enabled
            ),
            morning_explanation_batch_cron=morning_explanation_batch_cron,
        ),
        worker_id="worker-test-explanation",
        scheduler_factory=_scheduler_factory,
    )


def test_morning_explanation_batch_job_not_registered_by_default() -> None:
    scheduler = _build_with_explanation_batch_trigger()
    try:
        scheduler.start()
        assert (
            scheduler._scheduler.get_job("morning_explanation_batch_trigger") is None
        )
    finally:
        scheduler.stop()


def test_morning_explanation_batch_job_registered_when_enabled() -> None:
    scheduler = _build_with_explanation_batch_trigger(
        morning_explanation_batch_trigger_enabled=True,
        morning_explanation_batch_cron="45 6 * * *",
    )
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job("morning_explanation_batch_trigger")
        assert job is not None
        cron_repr = repr(job.trigger)
        assert "hour='6'" in cron_repr
        assert "minute='45'" in cron_repr
        assert "Europe/Brussels" in cron_repr
        _assert_explicit_guards(job)
    finally:
        scheduler.stop()


def test_morning_explanation_batch_handler_calls_trigger(monkeypatch) -> None:
    captured: list[dict[str, object]] = []
    from portfolio_outlook_worker import scheduler as sched_mod

    def _stub_trigger(*, base_url, timeout_seconds):
        captured.append({"base_url": base_url, "timeout": timeout_seconds})
        return {"status": "ok"}

    monkeypatch.setattr(
        sched_mod, "trigger_morning_explanation_batch", _stub_trigger
    )

    scheduler = _build_with_explanation_batch_trigger(
        morning_explanation_batch_trigger_enabled=True,
        api_base_url="http://api.local",
    )
    try:
        scheduler.start()
        scheduler._on_morning_explanation_batch_trigger()
        assert len(captured) == 1
        assert captured[0]["base_url"] == "http://api.local"
    finally:
        scheduler.stop()


def test_pre_briefing_tail_calls_morning_chain_when_configured(monkeypatch) -> None:
    """#2 — signal chaining: when ``morning_chain_after_pre_briefing`` is
    on, the pre-briefing handler must fire the morning chain trigger
    right after the audit row lands. The trigger function is stubbed so
    no HTTP actually leaves the process."""

    captured: list[dict[str, object]] = []

    from portfolio_outlook_worker import scheduler as sched_mod

    def _stub_trigger(*, base_url, timeout_seconds):
        captured.append({"base_url": base_url, "timeout": timeout_seconds})
        return {"status": "ok"}

    monkeypatch.setattr(sched_mod, "trigger_morning_chain", _stub_trigger)

    scheduler = _build_with_api_triggers(
        morning_chain_trigger_enabled=True,
        morning_chain_after_pre_briefing=True,
        api_base_url="http://api.local",
    )
    try:
        scheduler.start()
        # _on_pre_briefing calls _run + the tail call. _run early-exits
        # because storage is disabled in the test settings, so we only
        # exercise the tail-call branch.
        scheduler._on_pre_briefing()
        assert len(captured) == 1
        assert captured[0]["base_url"] == "http://api.local"
    finally:
        scheduler.stop()


def test_pre_briefing_does_not_tail_call_when_flag_off(monkeypatch) -> None:
    captured: list[object] = []
    from portfolio_outlook_worker import scheduler as sched_mod

    monkeypatch.setattr(
        sched_mod,
        "trigger_morning_chain",
        lambda **_: captured.append("called"),
    )
    scheduler = _build_with_api_triggers(morning_chain_trigger_enabled=True)
    try:
        scheduler.start()
        scheduler._on_pre_briefing()
        assert captured == []
    finally:
        scheduler.stop()


# ---- #8 — persistent sweep failures escalate to SystemEvents ------------


def _build_for_sweep_tracking() -> PortfolioScheduler:
    return PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(sweep_alert_after_consecutive_errors=3),
        scheduler_settings=SchedulerSettings(enabled=True),
        worker_id="worker-test",
        scheduler_factory=_scheduler_factory,
    )


def test_sweep_error_streak_fires_alert_at_threshold(monkeypatch) -> None:
    captured: list[dict[str, object]] = []
    from portfolio_outlook_worker import scheduler as sched_mod

    def _record(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(sched_mod, "record_worker_error", _record)
    scheduler = _build_for_sweep_tracking()

    # Two errors: below threshold, no alert.
    scheduler._track_sweep_outcome(kind="submission", mode="error", error_message="x")
    scheduler._track_sweep_outcome(kind="submission", mode="error", error_message="x")
    assert captured == []
    # Third error hits threshold: alert fires.
    scheduler._track_sweep_outcome(kind="submission", mode="error", error_message="x")
    assert len(captured) == 1
    assert "submission" in captured[0]["source_component"]
    assert captured[0]["event_code"] == "sweep_persistent_error"


def test_sweep_alert_is_debounced(monkeypatch) -> None:
    """After the first alert fires further consecutive errors must not
    re-alert — operators don't need 50 copies of the same notification."""

    captured: list[object] = []
    from portfolio_outlook_worker import scheduler as sched_mod

    monkeypatch.setattr(sched_mod, "record_worker_error", lambda **kw: captured.append(kw))
    scheduler = _build_for_sweep_tracking()

    for _ in range(10):
        scheduler._track_sweep_outcome(kind="submission", mode="error", error_message="x")
    assert len(captured) == 1


def test_sweep_streak_resets_on_non_error_tick(monkeypatch) -> None:
    """A successful tick clears the streak + the debounce so a future
    failure run can re-alert."""

    captured: list[object] = []
    from portfolio_outlook_worker import scheduler as sched_mod

    monkeypatch.setattr(sched_mod, "record_worker_error", lambda **kw: captured.append(kw))
    scheduler = _build_for_sweep_tracking()

    # Trip the alert.
    for _ in range(3):
        scheduler._track_sweep_outcome(kind="submission", mode="error", error_message="x")
    assert len(captured) == 1
    # A clean tick resets state.
    scheduler._track_sweep_outcome(kind="submission", mode="completed", error_message=None)
    # A new failure run re-alerts after another N consecutive errors.
    for _ in range(3):
        scheduler._track_sweep_outcome(kind="submission", mode="error", error_message="y")
    assert len(captured) == 2


def test_sweep_streak_is_per_kind(monkeypatch) -> None:
    """Submission and cancel sweeps each get their own counter — a
    flaky cancel sweep must not prevent the submission sweep from
    alerting (or vice versa)."""

    captured: list[dict[str, object]] = []
    from portfolio_outlook_worker import scheduler as sched_mod

    monkeypatch.setattr(sched_mod, "record_worker_error", lambda **kw: captured.append(kw))
    scheduler = _build_for_sweep_tracking()

    scheduler._track_sweep_outcome(kind="submission", mode="error", error_message="x")
    scheduler._track_sweep_outcome(kind="cancel", mode="error", error_message="y")
    scheduler._track_sweep_outcome(kind="submission", mode="error", error_message="x")
    scheduler._track_sweep_outcome(kind="cancel", mode="error", error_message="y")
    scheduler._track_sweep_outcome(kind="submission", mode="error", error_message="x")
    scheduler._track_sweep_outcome(kind="cancel", mode="error", error_message="y")
    components = sorted(c["source_component"] for c in captured)
    assert components == ["scheduler:cancel_sweep", "scheduler:submission_sweep"]


# ---- #8 — in-tick retry with exponential backoff ------------------------


class _Result:
    def __init__(self, mode: str) -> None:
        self.mode = mode


def test_retry_helper_returns_first_success_without_sleeping() -> None:
    from portfolio_outlook_worker.scheduler import _run_sweep_with_backoff

    slept: list[float] = []
    result = _run_sweep_with_backoff(
        attempt=lambda: _Result("completed"),
        max_attempts=3,
        base_backoff_seconds=2.0,
        sleep_fn=slept.append,
    )
    assert result.mode == "completed"
    assert slept == []  # never slept because first attempt succeeded


def test_retry_helper_retries_on_error_then_succeeds() -> None:
    from portfolio_outlook_worker.scheduler import _run_sweep_with_backoff

    sequence = iter([_Result("error"), _Result("error"), _Result("completed")])
    slept: list[float] = []
    result = _run_sweep_with_backoff(
        attempt=lambda: next(sequence),
        max_attempts=3,
        base_backoff_seconds=2.0,
        sleep_fn=slept.append,
    )
    assert result.mode == "completed"
    # Exponential backoff between attempts: 2s, 4s.
    assert slept == [2.0, 4.0]


def test_retry_helper_exhausts_attempts_and_returns_last_error() -> None:
    from portfolio_outlook_worker.scheduler import _run_sweep_with_backoff

    sequence = iter(
        [_Result("error"), _Result("error"), _Result("error"), _Result("completed")]
    )
    slept: list[float] = []
    result = _run_sweep_with_backoff(
        attempt=lambda: next(sequence),
        max_attempts=3,
        base_backoff_seconds=1.0,
        sleep_fn=slept.append,
    )
    # Only 3 attempts allowed — the would-be 4th success is never reached.
    assert result.mode == "error"
    assert slept == [1.0, 2.0]  # two sleeps between the three attempts


def test_retry_helper_treats_max_attempts_below_one_as_one() -> None:
    """A misconfigured ``sweep_retry_max_attempts=0`` must not skip the
    sweep entirely — clamp to at least one attempt."""

    from portfolio_outlook_worker.scheduler import _run_sweep_with_backoff

    calls = [0]

    def _attempt() -> _Result:
        calls[0] += 1
        return _Result("completed")

    _run_sweep_with_backoff(
        attempt=_attempt,
        max_attempts=0,
        base_backoff_seconds=1.0,
        sleep_fn=lambda _: None,
    )
    assert calls == [1]


class _ResultWithCode:
    """Test fake for sweep result with IBKR errorCode field."""

    def __init__(self, mode: str, error_code: int | None = None) -> None:
        self.mode = mode
        self.error_code = error_code


def test_retry_helper_uses_60s_minimum_backoff_on_ibkr_pacing_code_162() -> None:
    """Audit-correctie 2026-06-16: IBKR pacing-errorcode 162 MOET
    minimaal 60 seconden backoff krijgen i.p.v. de generieke 2/4/8s.
    Blind exponential werkt averechts bij pacing."""

    from portfolio_outlook_worker.scheduler import _run_sweep_with_backoff

    slept: list[float] = []

    def _attempt() -> _ResultWithCode:
        if not slept:
            return _ResultWithCode("error", error_code=162)
        return _ResultWithCode("completed")

    _run_sweep_with_backoff(
        attempt=_attempt,
        max_attempts=3,
        base_backoff_seconds=2.0,
        sleep_fn=slept.append,
    )
    assert len(slept) == 1
    assert slept[0] >= 60.0


def test_retry_helper_uses_60s_minimum_backoff_on_ibkr_pacing_code_100() -> None:
    """ErrorCode 100 (Max rate of messages per second) is ook pacing."""

    from portfolio_outlook_worker.scheduler import _run_sweep_with_backoff

    slept: list[float] = []

    def _attempt() -> _ResultWithCode:
        if not slept:
            return _ResultWithCode("error", error_code=100)
        return _ResultWithCode("completed")

    _run_sweep_with_backoff(
        attempt=_attempt,
        max_attempts=2,
        base_backoff_seconds=2.0,
        sleep_fn=slept.append,
    )
    assert len(slept) == 1
    assert slept[0] >= 60.0


def test_retry_helper_uses_60s_minimum_backoff_on_ibkr_pacing_code_420() -> None:
    """ErrorCode 420 (sustained order pacing) is ook pacing."""

    from portfolio_outlook_worker.scheduler import _run_sweep_with_backoff

    slept: list[float] = []

    def _attempt() -> _ResultWithCode:
        if not slept:
            return _ResultWithCode("error", error_code=420)
        return _ResultWithCode("completed")

    _run_sweep_with_backoff(
        attempt=_attempt,
        max_attempts=2,
        base_backoff_seconds=2.0,
        sleep_fn=slept.append,
    )
    assert slept[0] >= 60.0


def test_retry_helper_uses_exponential_for_connectivity_code_1100() -> None:
    """ErrorCode 1100 (Connectivity lost) MAG snel retry'en — TWS kan
    binnen seconden weer beschikbaar zijn, geen pacing-window."""

    from portfolio_outlook_worker.scheduler import _run_sweep_with_backoff

    slept: list[float] = []

    def _attempt() -> _ResultWithCode:
        if not slept:
            return _ResultWithCode("error", error_code=1100)
        return _ResultWithCode("completed")

    _run_sweep_with_backoff(
        attempt=_attempt,
        max_attempts=2,
        base_backoff_seconds=2.0,
        sleep_fn=slept.append,
    )
    # 2.0 * 2 ** (1 - 1) = 2.0 — connectivity blijft snel.
    assert slept == [2.0]


def test_retry_helper_falls_back_to_exponential_when_no_error_code() -> None:
    """Generieke error zonder code (legacy sweeps zonder error_code
    field) blijft de oude 2/4/8 backoff gebruiken — backwards-compat."""

    from portfolio_outlook_worker.scheduler import _run_sweep_with_backoff

    slept: list[float] = []

    def _attempt() -> _Result:
        if not slept:
            return _Result("error")
        return _Result("completed")

    _run_sweep_with_backoff(
        attempt=_attempt,
        max_attempts=2,
        base_backoff_seconds=2.0,
        sleep_fn=slept.append,
    )
    assert slept == [2.0]


# ---- SELL-signal sweep trigger (V1.2 §BI) ---------------------------


def _build_with_sell_sweep_trigger(
    *,
    sell_signal_sweep_trigger_enabled: bool = False,
    sell_signal_sweep_cron: str = "*/10 7-22 * * mon-fri",
    api_base_url: str | None = "http://api:8000",
) -> PortfolioScheduler:
    return PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
            api_base_url=api_base_url,
            sell_signal_sweep_trigger_enabled=sell_signal_sweep_trigger_enabled,
            sell_signal_sweep_cron=sell_signal_sweep_cron,
        ),
        worker_id="worker-test-sell-sweep",
        scheduler_factory=_scheduler_factory,
    )


def test_sell_signal_sweep_job_not_registered_by_default() -> None:
    scheduler = _build_with_sell_sweep_trigger()
    try:
        scheduler.start()
        assert (
            scheduler._scheduler.get_job("sell_signal_sweep_trigger") is None
        )
    finally:
        scheduler.stop()


def test_sell_signal_sweep_job_registered_when_enabled() -> None:
    """V1.2 §BI — wanneer de flag aan staat moet de cron op
    elke 10 min weekdagen 07:00-22:00 Europe/Brussels staan."""

    scheduler = _build_with_sell_sweep_trigger(
        sell_signal_sweep_trigger_enabled=True,
        sell_signal_sweep_cron="*/10 7-22 * * mon-fri",
    )
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job("sell_signal_sweep_trigger")
        assert job is not None
        cron_repr = repr(job.trigger)
        assert "minute='*/10'" in cron_repr
        assert "hour='7-22'" in cron_repr
        assert "day_of_week='mon-fri'" in cron_repr
        assert "Europe/Brussels" in cron_repr
        _assert_explicit_guards(job)
    finally:
        scheduler.stop()


def test_sell_signal_sweep_handler_calls_trigger(monkeypatch) -> None:
    """De cron handler moet de api_trigger functie aanroepen met de
    geconfigureerde base_url + timeout."""

    captured: list[dict[str, object]] = []
    from portfolio_outlook_worker import scheduler as sched_mod

    def _stub_trigger(*, base_url, timeout_seconds):
        captured.append({"base_url": base_url, "timeout": timeout_seconds})
        return {"status": "ok"}

    monkeypatch.setattr(sched_mod, "trigger_sell_signal_sweep", _stub_trigger)

    scheduler = _build_with_sell_sweep_trigger(
        sell_signal_sweep_trigger_enabled=True,
        api_base_url="http://api.local",
    )
    try:
        scheduler.start()
        scheduler._on_sell_signal_sweep_trigger()
        assert len(captured) == 1
        assert captured[0]["base_url"] == "http://api.local"
    finally:
        scheduler.stop()


def test_sell_signal_sweep_cron_rejects_bad_expression() -> None:
    """Een verkeerd-aantal velden moet vroeg falen, niet in productie."""

    scheduler = _build_with_sell_sweep_trigger(
        sell_signal_sweep_trigger_enabled=True,
        sell_signal_sweep_cron="bad cron",
    )
    import pytest

    with pytest.raises(ValueError, match="sell_signal_sweep_cron"):
        scheduler.start()


# ---- Monthly archive auto-generate (V1.2 §BN) -----------------------


def _build_with_monthly_archive_trigger(
    *,
    monthly_archive_auto_generate_enabled: bool = False,
    monthly_archive_auto_generate_cron: str = "15 0 1 * *",
    api_base_url: str | None = "http://api:8000",
) -> PortfolioScheduler:
    return PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
            api_base_url=api_base_url,
            monthly_archive_auto_generate_enabled=(
                monthly_archive_auto_generate_enabled
            ),
            monthly_archive_auto_generate_cron=monthly_archive_auto_generate_cron,
        ),
        worker_id="worker-test-monthly-archive",
        scheduler_factory=_scheduler_factory,
    )


def test_monthly_archive_job_not_registered_by_default() -> None:
    scheduler = _build_with_monthly_archive_trigger()
    try:
        scheduler.start()
        assert (
            scheduler._scheduler.get_job("monthly_archive_auto_generate") is None
        )
    finally:
        scheduler.stop()


def test_monthly_archive_job_registered_when_enabled() -> None:
    """V1.2 §BN — cron op 00:15 op de 1e van elke maand."""

    scheduler = _build_with_monthly_archive_trigger(
        monthly_archive_auto_generate_enabled=True,
        monthly_archive_auto_generate_cron="15 0 1 * *",
    )
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job("monthly_archive_auto_generate")
        assert job is not None
        cron_repr = repr(job.trigger)
        assert "minute='15'" in cron_repr
        assert "hour='0'" in cron_repr
        assert "day='1'" in cron_repr
        assert "Europe/Brussels" in cron_repr
    finally:
        scheduler.stop()


def test_monthly_archive_handler_calls_trigger(monkeypatch) -> None:
    captured: list[dict[str, object]] = []
    from portfolio_outlook_worker import scheduler as sched_mod

    def _stub_trigger(*, base_url, timeout_seconds):
        captured.append({"base_url": base_url, "timeout": timeout_seconds})
        return {"status": "ok"}

    monkeypatch.setattr(
        sched_mod, "trigger_monthly_archive_auto_generate", _stub_trigger
    )
    scheduler = _build_with_monthly_archive_trigger(
        monthly_archive_auto_generate_enabled=True,
        api_base_url="http://api.local",
    )
    try:
        scheduler.start()
        scheduler._on_monthly_archive_auto_generate_trigger()
        assert len(captured) == 1
        assert captured[0]["base_url"] == "http://api.local"
    finally:
        scheduler.stop()


def test_monthly_archive_cron_rejects_bad_expression() -> None:
    scheduler = _build_with_monthly_archive_trigger(
        monthly_archive_auto_generate_enabled=True,
        monthly_archive_auto_generate_cron="bad",
    )
    import pytest

    with pytest.raises(ValueError, match="monthly_archive_auto_generate_cron"):
        scheduler.start()


# ---- Macro feed refresh (V1.2 §BT / GAPS.md P1-10) -----------------


def _build_with_macro_feed_trigger(
    *,
    macro_feed_refresh_enabled: bool = False,
    macro_feed_refresh_cron: str = "30 17 * * mon-fri",
    api_base_url: str | None = "http://api:8000",
) -> PortfolioScheduler:
    return PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
            api_base_url=api_base_url,
            macro_feed_refresh_enabled=macro_feed_refresh_enabled,
            macro_feed_refresh_cron=macro_feed_refresh_cron,
        ),
        worker_id="worker-test-macro",
        scheduler_factory=_scheduler_factory,
    )


def test_macro_feed_refresh_job_not_registered_by_default() -> None:
    scheduler = _build_with_macro_feed_trigger()
    try:
        scheduler.start()
        assert scheduler._scheduler.get_job("macro_feed_refresh") is None
    finally:
        scheduler.stop()


def test_macro_feed_refresh_job_registered_when_enabled() -> None:
    scheduler = _build_with_macro_feed_trigger(
        macro_feed_refresh_enabled=True,
        macro_feed_refresh_cron="30 17 * * mon-fri",
    )
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job("macro_feed_refresh")
        assert job is not None
        cron_repr = repr(job.trigger)
        assert "minute='30'" in cron_repr
        assert "hour='17'" in cron_repr
        assert "day_of_week='mon-fri'" in cron_repr
        assert "Europe/Brussels" in cron_repr
    finally:
        scheduler.stop()


def test_macro_feed_refresh_handler_calls_trigger(monkeypatch) -> None:
    captured: list[dict[str, object]] = []
    from portfolio_outlook_worker import scheduler as sched_mod

    def _stub_trigger(*, base_url, timeout_seconds):
        captured.append({"base_url": base_url, "timeout": timeout_seconds})
        return {"status": "ok"}

    monkeypatch.setattr(sched_mod, "trigger_macro_feed_refresh", _stub_trigger)
    scheduler = _build_with_macro_feed_trigger(
        macro_feed_refresh_enabled=True,
        api_base_url="http://api.local",
    )
    try:
        scheduler.start()
        scheduler._on_macro_feed_refresh_trigger()
        assert len(captured) == 1
        assert captured[0]["base_url"] == "http://api.local"
    finally:
        scheduler.stop()


# ---- Reconciliation sweep trigger (V1.2 §BM / GAPS.md P0-3) ---------


class _ReconcilerStubGateway:
    """V1.2 §BM — gateway double for the in-process reconciler tests.

    Exposes both ``is_connected`` (used by IbkrReconcilerGatewayProtocol)
    and ``get_read_ib_client`` (used by the scheduler to feed the
    reconciler fetchers). The "ib_client" returned is a sentinel that
    the test's ``run_reconciler_tick`` stub asserts against.
    """

    def __init__(self, *, connected: bool, ib_client: object | None) -> None:
        self._connected = connected
        self._ib_client = ib_client

    def is_connected(self) -> bool:
        return self._connected

    def get_read_ib_client(self) -> object | None:
        return self._ib_client if self._connected else None


def _build_with_reconciliation_sweep_trigger(
    *,
    reconciliation_sweep_trigger_enabled: bool = False,
    reconciliation_sweep_cron: str = "*/30 * * * mon-fri",
    storage_enabled: bool = False,
    storage_database_url: str | None = None,
    ibkr_account_id: str | None = None,
    gateway_connected: bool = True,
    use_dedicated_reconciler_gateway: bool = False,
) -> PortfolioScheduler:
    """Build a scheduler for reconciliation-sweep tests.

    ``use_dedicated_reconciler_gateway=True`` mirrors production wiring
    after V1.2 §BM-2 refactor: the main gateway is the disconnected
    boot-stub, and the reconciliation cron uses a separate connected
    ``reconciler_gateway``. Default ``False`` keeps the pre-refactor
    behaviour where the main gateway carries the ib_client (the
    backwards-compat path).
    """

    main_gateway = _ReconcilerStubGateway(
        connected=gateway_connected and not use_dedicated_reconciler_gateway,
        ib_client=(
            object()
            if gateway_connected and not use_dedicated_reconciler_gateway
            else None
        ),
    )
    reconciler_gateway = (
        _ReconcilerStubGateway(
            connected=gateway_connected,
            ib_client=object() if gateway_connected else None,
        )
        if use_dedicated_reconciler_gateway
        else None
    )
    return PortfolioScheduler(
        gateway=main_gateway,
        reconciler_gateway=reconciler_gateway,
        storage_settings=StorageSettings(
            enabled=storage_enabled,
            database_url=storage_database_url,
            writes_enabled=storage_enabled,
        ),
        ibkr_settings=IbkrSettings(account_id=ibkr_account_id),
        scheduler_settings=SchedulerSettings(
            enabled=True,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
            reconciliation_sweep_trigger_enabled=(
                reconciliation_sweep_trigger_enabled
            ),
            reconciliation_sweep_cron=reconciliation_sweep_cron,
        ),
        worker_id="worker-test-reconciliation-sweep",
        scheduler_factory=_scheduler_factory,
    )


def test_reconciliation_sweep_job_not_registered_by_default() -> None:
    scheduler = _build_with_reconciliation_sweep_trigger()
    try:
        scheduler.start()
        assert (
            scheduler._scheduler.get_job("reconciliation_sweep_trigger") is None
        )
    finally:
        scheduler.stop()


def test_reconciliation_sweep_job_registered_when_enabled() -> None:
    """V1.2 §BM / GAPS.md P0-3 — wanneer de flag aan staat moet de
    cron op elke 30 min weekdagen Europe/Brussels staan."""

    scheduler = _build_with_reconciliation_sweep_trigger(
        reconciliation_sweep_trigger_enabled=True,
        reconciliation_sweep_cron="*/30 * * * mon-fri",
    )
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job("reconciliation_sweep_trigger")
        assert job is not None
        cron_repr = repr(job.trigger)
        assert "minute='*/30'" in cron_repr
        assert "day_of_week='mon-fri'" in cron_repr
        assert "Europe/Brussels" in cron_repr
        _assert_explicit_guards(job)
    finally:
        scheduler.stop()


def test_reconciliation_sweep_handler_calls_trigger(monkeypatch) -> None:
    """De cron handler moet ``trigger_reconciliation_sweep`` aanroepen
    met de geconfigureerde base_url + timeout."""

    captured: list[dict[str, object]] = []
    from portfolio_outlook_worker.ibkr_reconciliation import (
        reconciler_runner as runner_mod,
    )

    class _Result:
        mode_detected = "completed"
        pass_a_orphaned_count = 0
        pass_b_stale_count = 0
        pass_c_timeout_count = 0
        error_details_json = None

    def _stub_tick(**kwargs):
        captured.append(kwargs)
        return _Result()

    monkeypatch.setattr(runner_mod, "run_reconciler_tick", _stub_tick)
    monkeypatch.setattr(
        runner_mod, "build_storage_provider", lambda _url: object()
    )

    scheduler = _build_with_reconciliation_sweep_trigger(
        reconciliation_sweep_trigger_enabled=True,
        ibkr_account_id="DU12345",
        storage_enabled=False,  # keep heartbeat off
    )
    try:
        scheduler.start()
        # Override the storage_settings post-start so the reconciliation
        # handler's storage-enabled guard passes — the heartbeat that
        # ran during ``start()`` already skipped on the original False.
        scheduler._storage_settings = StorageSettings(
            enabled=True,
            database_url="postgresql://fake",
            writes_enabled=True,
        )
        scheduler._on_reconciliation_sweep_trigger()
        assert len(captured) == 1
        # The runner was called with the in-process gateway + the lock
        # factory from the scheduler module, not a base_url.
        assert captured[0]["ibkr_account_id"] == "DU12345"
        assert "storage_provider" in captured[0]
        assert "ib_client" in captured[0]
        assert "lock_factory" in captured[0]
        assert "pass_c_timeout_cutoff" in captured[0]
    finally:
        scheduler.stop()


def test_reconciliation_sweep_skipped_without_account_id(monkeypatch) -> None:
    """Geen ``account_id`` configured → cron skip't zonder runner-call,
    geen warning of fout."""

    from portfolio_outlook_worker.ibkr_reconciliation import (
        reconciler_runner as runner_mod,
    )

    called: list[dict] = []

    def _stub_tick(**kwargs):
        called.append(kwargs)
        return None

    monkeypatch.setattr(runner_mod, "run_reconciler_tick", _stub_tick)
    monkeypatch.setattr(
        runner_mod, "build_storage_provider", lambda _url: object()
    )

    scheduler = _build_with_reconciliation_sweep_trigger(
        reconciliation_sweep_trigger_enabled=True,
        storage_enabled=False,
        # account_id intentionally left None
    )
    try:
        scheduler.start()
        scheduler._storage_settings = StorageSettings(
            enabled=True,
            database_url="postgresql://fake",
            writes_enabled=True,
        )
        scheduler._on_reconciliation_sweep_trigger()
        assert called == []
    finally:
        scheduler.stop()


def test_reconciliation_sweep_skipped_when_gateway_disconnected(
    monkeypatch,
) -> None:
    """Gateway niet verbonden → cron skip't; geen IBKR-call gemaakt."""

    from portfolio_outlook_worker.ibkr_reconciliation import (
        reconciler_runner as runner_mod,
    )

    called: list[dict] = []

    def _stub_tick(**kwargs):
        called.append(kwargs)
        return None

    monkeypatch.setattr(runner_mod, "run_reconciler_tick", _stub_tick)
    monkeypatch.setattr(
        runner_mod, "build_storage_provider", lambda _url: object()
    )

    scheduler = _build_with_reconciliation_sweep_trigger(
        reconciliation_sweep_trigger_enabled=True,
        ibkr_account_id="DU12345",
        storage_enabled=False,
        gateway_connected=False,
    )
    try:
        scheduler.start()
        scheduler._storage_settings = StorageSettings(
            enabled=True,
            database_url="postgresql://fake",
            writes_enabled=True,
        )
        scheduler._on_reconciliation_sweep_trigger()
        assert called == []
    finally:
        scheduler.stop()


def test_reconciliation_sweep_prefers_dedicated_reconciler_gateway(
    monkeypatch,
) -> None:
    """V1.2 §BM-2 / GAPS.md P0-3 — wanneer een dedicated reconciler
    gateway is geinjecteerd (productie-pad), gebruikt de cron die,
    NIET de hoofdgateway (die in productie de disconnected boot-stub
    is)."""

    captured: list[dict[str, object]] = []
    from portfolio_outlook_worker.ibkr_reconciliation import (
        reconciler_runner as runner_mod,
    )

    class _Result:
        mode_detected = "completed"
        pass_a_orphaned_count = 0
        pass_b_stale_count = 0
        pass_c_timeout_count = 0
        error_details_json = None

    def _stub_tick(**kwargs):
        captured.append(kwargs)
        return _Result()

    monkeypatch.setattr(runner_mod, "run_reconciler_tick", _stub_tick)
    monkeypatch.setattr(
        runner_mod, "build_storage_provider", lambda _url: object()
    )

    scheduler = _build_with_reconciliation_sweep_trigger(
        reconciliation_sweep_trigger_enabled=True,
        ibkr_account_id="DU12345",
        storage_enabled=False,  # heartbeat off
        use_dedicated_reconciler_gateway=True,
    )
    # Confirm the main gateway is disconnected (production matches this
    # after the refactor — _try_connect_ibkr discards its session).
    assert scheduler._gateway.is_connected() is False
    # And the dedicated reconciler gateway IS connected.
    assert scheduler._reconciler_gateway is not None
    assert scheduler._reconciler_gateway.is_connected() is True

    try:
        scheduler.start()
        scheduler._storage_settings = StorageSettings(
            enabled=True,
            database_url="postgresql://fake",
            writes_enabled=True,
        )
        scheduler._on_reconciliation_sweep_trigger()
        assert len(captured) == 1
        # Critical: the gateway passed to run_reconciler_tick is the
        # dedicated reconciler one, NOT the main gateway.
        assert captured[0]["gateway"] is scheduler._reconciler_gateway
        assert captured[0]["gateway"] is not scheduler._gateway
    finally:
        scheduler.stop()


def test_reconciliation_sweep_cron_rejects_bad_expression() -> None:
    """Een verkeerd-aantal velden moet vroeg falen, niet in productie."""

    import pytest

    scheduler = _build_with_reconciliation_sweep_trigger(
        reconciliation_sweep_trigger_enabled=True,
        reconciliation_sweep_cron="bad cron",
    )
    with pytest.raises(ValueError, match="reconciliation_sweep_cron"):
        scheduler.start()
