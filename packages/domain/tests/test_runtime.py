from datetime import datetime, UTC

import pytest
from pydantic import BaseModel, ValidationError

from portfolio_outlook_domain.enums import (
    ParallelExecutionPolicy,
    RuntimeDeploymentTarget,
    RuntimeHealthSeverity,
    RuntimeResourceProfile,
    RuntimeServiceCriticality,
    RuntimeServiceKind,
    RuntimeServiceStatus,
    ServiceFailurePolicy,
    StartupDependencyPolicy,
    StartupPhase,
)
from portfolio_outlook_domain.identifiers import BackgroundJobTypeId, HealthCheckId, RuntimeServiceId
from portfolio_outlook_domain.runtime import (
    BackgroundJobType,
    RuntimeServiceDefinition,
    RuntimeServiceHealth,
    RuntimeTopology,
    StartupPlan,
    StartupPlanStep,
    build_default_background_job_types,
    build_default_runtime_topology,
    find_service,
    parallel_safe_services,
    required_services,
    service_blocks_suggestions,
)


class _RuntimeServiceIdModel(BaseModel):
    value: RuntimeServiceId


class _HealthCheckIdModel(BaseModel):
    value: HealthCheckId


class _BackgroundJobTypeIdModel(BaseModel):
    value: BackgroundJobTypeId


def test_runtime_identifiers_accept_and_reject() -> None:
    assert _RuntimeServiceIdModel(value="svc_api").value == "svc_api"
    assert _HealthCheckIdModel(value="hc_1").value == "hc_1"
    assert _BackgroundJobTypeIdModel(value="job-1").value == "job-1"

    with pytest.raises(ValidationError):
        _RuntimeServiceIdModel(value="")

    with pytest.raises(ValidationError):
        _HealthCheckIdModel(value="bad id")


def _valid_service() -> RuntimeServiceDefinition:
    return RuntimeServiceDefinition(
        runtime_service_id="svc_test",
        service_kind=RuntimeServiceKind.API,
        service_name="Test",
        criticality=RuntimeServiceCriticality.REQUIRED,
        startup_phase=StartupPhase.API,
        startup_dependency_policy=StartupDependencyPolicy.INDEPENDENT,
        resource_profile=RuntimeResourceProfile.LIGHTWEIGHT,
        parallel_execution_policy=ParallelExecutionPolicy.PARALLEL_SAFE,
        failure_policy=ServiceFailurePolicy.BLOCK_SUGGESTIONS,
        enabled_by_default=True,
        explanation_nl="Uitleg",
    )


def test_runtime_service_definition_validation() -> None:
    model = _valid_service()
    assert model.model_dump()["runtime_service_id"] == "svc_test"

    with pytest.raises(ValidationError):
        _valid_service().model_copy(update={"service_name": " "})

    with pytest.raises(ValidationError):
        RuntimeServiceDefinition(**(_valid_service().model_dump() | {"enabled_by_default": False}))

    with pytest.raises(ValidationError):
        RuntimeServiceDefinition(**(_valid_service().model_dump() | {"dependency_service_ids": ["svc_test"]}))

    with pytest.raises(ValidationError):
        RuntimeServiceDefinition(**(_valid_service().model_dump() | {"resource_profile": RuntimeResourceProfile.HEAVY, "parallel_execution_policy": ParallelExecutionPolicy.PARALLEL_SAFE}))


def test_runtime_service_health_validation() -> None:
    health = RuntimeServiceHealth(
        health_check_id="hc_api",
        runtime_service_id="svc_test",
        status=RuntimeServiceStatus.HEALTHY,
        severity=RuntimeHealthSeverity.OK,
        checked_at=datetime.now(tz=UTC),
        message_nl="Actief",
        blocks_new_suggestions=False,
    )
    assert health.model_dump()["message_nl"] == "Actief"

    with pytest.raises(ValidationError):
        RuntimeServiceHealth(**(health.model_dump() | {"message_nl": " "}))

    with pytest.raises(ValidationError):
        RuntimeServiceHealth(**(health.model_dump() | {"severity": RuntimeHealthSeverity.CRITICAL, "blocks_new_suggestions": False}))


def test_startup_plan_validation() -> None:
    step = StartupPlanStep(
        step_order=1,
        startup_phase=StartupPhase.API,
        runtime_service_id="svc_test",
        required=True,
        explanation_nl="Start api",
    )
    plan = StartupPlan(
        startup_plan_id="plan_1",
        plan_name="Plan",
        target=RuntimeDeploymentTarget.RASPBERRY_PI_5,
        steps=[step],
        created_at=datetime.now(tz=UTC),
    )
    assert plan.model_dump()["plan_name"] == "Plan"

    with pytest.raises(ValidationError):
        StartupPlan(**(plan.model_dump() | {"steps": []}))

    with pytest.raises(ValidationError):
        StartupPlan(**(plan.model_dump() | {"steps": [step, step.model_copy(update={"runtime_service_id": "svc_test_2"})]}))


def test_runtime_topology_and_helpers() -> None:
    created_at = datetime.now(tz=UTC)
    topology = build_default_runtime_topology(created_at=created_at)
    assert topology.services
    assert find_service(topology, RuntimeServiceKind.API) is not None
    assert find_service(topology, RuntimeServiceKind.UNKNOWN) is None
    assert required_services(topology)
    assert all(s.criticality is RuntimeServiceCriticality.REQUIRED for s in required_services(topology))
    assert all(s.resource_profile is not RuntimeResourceProfile.HEAVY for s in parallel_safe_services(topology))

    for kind in [
        RuntimeServiceKind.WORKER,
        RuntimeServiceKind.WEB_FRONTEND,
        RuntimeServiceKind.HEALTH_MONITOR,
        RuntimeServiceKind.AUDIT_LOGGER,
        RuntimeServiceKind.SCHEDULER,
        RuntimeServiceKind.DATA_SOURCE_UPDATER,
        RuntimeServiceKind.RESEARCH_WORKER,
        RuntimeServiceKind.AI_RESEARCH_QUEUE,
        RuntimeServiceKind.IBKR_ADAPTER,
        RuntimeServiceKind.BACKUP_SERVICE,
    ]:
        assert find_service(topology, kind) is not None

    with pytest.raises(ValidationError):
        RuntimeTopology(**(topology.model_dump() | {"services": topology.services + [topology.services[0]]}))


def test_background_jobs_and_blocking_logic() -> None:
    jobs = build_default_background_job_types()
    assert jobs
    by_id = {job.background_job_type_id: job for job in jobs}
    assert "job_ai_research_run" in by_id
    assert by_id["job_ai_research_run"].requires_queue is True
    assert by_id["job_backup_check"].parallel_execution_policy is ParallelExecutionPolicy.SCHEDULED_ONLY
    assert all("uitvoering" not in j.explanation_nl.lower() or "zonder" in j.explanation_nl.lower() for j in jobs)

    service = _valid_service()
    critical_health = RuntimeServiceHealth(
        health_check_id="hc_crit",
        runtime_service_id="svc_test",
        status=RuntimeServiceStatus.UNHEALTHY,
        severity=RuntimeHealthSeverity.CRITICAL,
        checked_at=datetime.now(tz=UTC),
        message_nl="Kritiek",
        blocks_new_suggestions=True,
    )
    assert service_blocks_suggestions(service, critical_health) is True

    optional_service = RuntimeServiceDefinition(
        runtime_service_id="svc_opt",
        service_kind=RuntimeServiceKind.REVERSE_PROXY,
        service_name="Opt",
        criticality=RuntimeServiceCriticality.OPTIONAL,
        startup_phase=StartupPhase.READY,
        startup_dependency_policy=StartupDependencyPolicy.INDEPENDENT,
        resource_profile=RuntimeResourceProfile.LIGHTWEIGHT,
        parallel_execution_policy=ParallelExecutionPolicy.PARALLEL_SAFE,
        failure_policy=ServiceFailurePolicy.DISABLE_OPTIONAL_FEATURE,
        enabled_by_default=False,
        explanation_nl="Optionele service",
    )
    degraded = RuntimeServiceHealth(
        health_check_id="hc_opt",
        runtime_service_id="svc_opt",
        status=RuntimeServiceStatus.DEGRADED,
        severity=RuntimeHealthSeverity.WARNING,
        checked_at=datetime.now(tz=UTC),
        message_nl="Degraded",
        blocks_new_suggestions=False,
    )
    assert service_blocks_suggestions(optional_service, degraded) is False

    with pytest.raises(ValidationError):
        BackgroundJobType(
            background_job_type_id="job_heavy",
            job_name="Heavy",
            service_kind=RuntimeServiceKind.WORKER,
            resource_profile=RuntimeResourceProfile.HEAVY,
            parallel_execution_policy=ParallelExecutionPolicy.QUEUE_REQUIRED,
            allowed_on_raspberry_pi_5=True,
            requires_queue=False,
            explanation_nl="Heavy",
        )
