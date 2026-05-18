from datetime import datetime

from pydantic import Field, model_validator

from .enums import (
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
from .identifiers import (
    BackgroundJobTypeId,
    HealthCheckId,
    RuntimeServiceId,
    RuntimeTopologyId,
    StartupPlanId,
)
from .primitives import DomainBaseModel


class RuntimeServiceDefinition(DomainBaseModel):
    runtime_service_id: RuntimeServiceId
    service_kind: RuntimeServiceKind
    service_name: str
    criticality: RuntimeServiceCriticality
    startup_phase: StartupPhase
    dependency_service_ids: list[RuntimeServiceId] = Field(default_factory=list)
    startup_dependency_policy: StartupDependencyPolicy
    resource_profile: RuntimeResourceProfile
    parallel_execution_policy: ParallelExecutionPolicy
    failure_policy: ServiceFailurePolicy
    enabled_by_default: bool
    explanation_nl: str

    @model_validator(mode="after")
    def validate_model(self) -> "RuntimeServiceDefinition":
        if not self.service_name.strip() or not self.explanation_nl.strip():
            raise ValueError("service_name en explanation_nl zijn verplicht")
        if (
            self.criticality is RuntimeServiceCriticality.REQUIRED
            and not self.enabled_by_default
        ):
            raise ValueError("required service moet enabled_by_default=True hebben")
        if self.runtime_service_id in self.dependency_service_ids:
            raise ValueError("service mag geen dependency op zichzelf hebben")
        if (
            self.resource_profile is RuntimeResourceProfile.HEAVY
            and self.parallel_execution_policy is ParallelExecutionPolicy.PARALLEL_SAFE
        ):
            raise ValueError("heavy service mag niet parallel_safe zijn")
        return self


class RuntimeServiceHealth(DomainBaseModel):
    health_check_id: HealthCheckId
    runtime_service_id: RuntimeServiceId
    status: RuntimeServiceStatus
    severity: RuntimeHealthSeverity
    checked_at: datetime
    message_nl: str
    blocks_new_suggestions: bool

    @model_validator(mode="after")
    def validate_model(self) -> "RuntimeServiceHealth":
        if not self.message_nl.strip():
            raise ValueError("message_nl is verplicht")
        if self.severity is RuntimeHealthSeverity.CRITICAL and not self.blocks_new_suggestions:
            raise ValueError("critical severity moet suggestions blokkeren")
        if (
            self.status is RuntimeServiceStatus.UNHEALTHY
            and self.severity in {RuntimeHealthSeverity.ERROR, RuntimeHealthSeverity.CRITICAL}
            and not self.blocks_new_suggestions
        ):
            raise ValueError("unhealthy + error/critical moet suggestions blokkeren")
        return self


class StartupPlanStep(DomainBaseModel):
    step_order: int
    startup_phase: StartupPhase
    runtime_service_id: RuntimeServiceId
    required: bool
    explanation_nl: str

    @model_validator(mode="after")
    def validate_model(self) -> "StartupPlanStep":
        if self.step_order <= 0:
            raise ValueError("step_order moet positief zijn")
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl is verplicht")
        return self


class StartupPlan(DomainBaseModel):
    startup_plan_id: StartupPlanId
    plan_name: str
    target: RuntimeDeploymentTarget
    steps: list[StartupPlanStep]
    created_at: datetime

    @model_validator(mode="after")
    def validate_model(self) -> "StartupPlan":
        if not self.plan_name.strip():
            raise ValueError("plan_name is verplicht")
        if not self.steps:
            raise ValueError("steps mogen niet leeg zijn")
        orders = [step.step_order for step in self.steps]
        if len(orders) != len(set(orders)):
            raise ValueError("duplicate step_order")
        return self


class RuntimeTopology(DomainBaseModel):
    runtime_topology_id: RuntimeTopologyId
    topology_name: str
    target: RuntimeDeploymentTarget
    services: list[RuntimeServiceDefinition]
    startup_plan: StartupPlan
    created_at: datetime

    @model_validator(mode="after")
    def validate_model(self) -> "RuntimeTopology":
        if not self.topology_name.strip() or not self.services:
            raise ValueError("topology_name en services zijn verplicht")
        service_ids = [service.runtime_service_id for service in self.services]
        if len(service_ids) != len(set(service_ids)):
            raise ValueError("duplicate runtime_service_id")
        known = set(service_ids)
        plan_ids = [step.runtime_service_id for step in self.startup_plan.steps]
        if not set(plan_ids).issubset(known):
            raise ValueError("startup plan bevat onbekende service")
        required_ids = {
            service.runtime_service_id
            for service in self.services
            if service.criticality is RuntimeServiceCriticality.REQUIRED
        }
        if not required_ids.issubset(set(plan_ids)):
            raise ValueError("required services moeten in startup plan staan")
        return self


class BackgroundJobType(DomainBaseModel):
    background_job_type_id: BackgroundJobTypeId
    job_name: str
    service_kind: RuntimeServiceKind
    resource_profile: RuntimeResourceProfile
    parallel_execution_policy: ParallelExecutionPolicy
    allowed_on_raspberry_pi_5: bool
    requires_queue: bool
    explanation_nl: str

    @model_validator(mode="after")
    def validate_model(self) -> "BackgroundJobType":
        if not self.job_name.strip() or not self.explanation_nl.strip():
            raise ValueError("job_name en explanation_nl zijn verplicht")
        if self.resource_profile is RuntimeResourceProfile.HEAVY and not self.requires_queue:
            raise ValueError("heavy jobs vereisen queue")
        return self


def build_default_runtime_topology(*, created_at: datetime) -> RuntimeTopology:
    services = [
        RuntimeServiceDefinition(runtime_service_id="svc_api", service_kind=RuntimeServiceKind.API, service_name="API", criticality=RuntimeServiceCriticality.REQUIRED, startup_phase=StartupPhase.API, startup_dependency_policy=StartupDependencyPolicy.MUST_START_BEFORE, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.PARALLEL_SAFE, failure_policy=ServiceFailurePolicy.BLOCK_SUGGESTIONS, enabled_by_default=True, explanation_nl="Deze service verwerkt verzoeken van de app en toont actuele gegevens."),
        RuntimeServiceDefinition(runtime_service_id="svc_worker", service_kind=RuntimeServiceKind.WORKER, service_name="Worker", criticality=RuntimeServiceCriticality.REQUIRED, startup_phase=StartupPhase.WORKER, dependency_service_ids=["svc_api"], startup_dependency_policy=StartupDependencyPolicy.SHOULD_START_BEFORE, resource_profile=RuntimeResourceProfile.MODERATE, parallel_execution_policy=ParallelExecutionPolicy.PARALLEL_SAFE, failure_policy=ServiceFailurePolicy.BLOCK_SUGGESTIONS, enabled_by_default=True, explanation_nl="Deze service verwerkt veilige achtergrondtaken zonder orders uit te voeren."),
        RuntimeServiceDefinition(runtime_service_id="svc_web", service_kind=RuntimeServiceKind.WEB_FRONTEND, service_name="Web frontend", criticality=RuntimeServiceCriticality.IMPORTANT, startup_phase=StartupPhase.READY, dependency_service_ids=["svc_api"], startup_dependency_policy=StartupDependencyPolicy.SHOULD_START_BEFORE, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.PARALLEL_SAFE, failure_policy=ServiceFailurePolicy.ALLOW_READ_ONLY, enabled_by_default=True, explanation_nl="Deze service toont de gebruikersinterface in de browser."),
        RuntimeServiceDefinition(runtime_service_id="svc_health", service_kind=RuntimeServiceKind.HEALTH_MONITOR, service_name="Health monitor", criticality=RuntimeServiceCriticality.REQUIRED, startup_phase=StartupPhase.MONITORING, startup_dependency_policy=StartupDependencyPolicy.INDEPENDENT, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.PARALLEL_SAFE, failure_policy=ServiceFailurePolicy.BLOCK_SUGGESTIONS, enabled_by_default=True, explanation_nl="Deze service bewaakt de gezondheid van onderdelen en meldt fouten."),
        RuntimeServiceDefinition(runtime_service_id="svc_audit", service_kind=RuntimeServiceKind.AUDIT_LOGGER, service_name="Audit logger", criticality=RuntimeServiceCriticality.REQUIRED, startup_phase=StartupPhase.MONITORING, startup_dependency_policy=StartupDependencyPolicy.INDEPENDENT, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.PARALLEL_SAFE, failure_policy=ServiceFailurePolicy.BLOCK_SUGGESTIONS, enabled_by_default=True, explanation_nl="Deze service logt beslissingen zodat controle mogelijk blijft."),
        RuntimeServiceDefinition(runtime_service_id="svc_db", service_kind=RuntimeServiceKind.DATABASE, service_name="Database", criticality=RuntimeServiceCriticality.FUTURE, startup_phase=StartupPhase.STORAGE, startup_dependency_policy=StartupDependencyPolicy.MUST_START_BEFORE, resource_profile=RuntimeResourceProfile.MODERATE, parallel_execution_policy=ParallelExecutionPolicy.NOT_PARALLEL, failure_policy=ServiceFailurePolicy.MANUAL_INTERVENTION_REQUIRED, enabled_by_default=False, explanation_nl="Deze toekomstige service bewaart gegevens duurzaam en herstelbaar."),
        RuntimeServiceDefinition(runtime_service_id="svc_scheduler", service_kind=RuntimeServiceKind.SCHEDULER, service_name="Scheduler", criticality=RuntimeServiceCriticality.FUTURE, startup_phase=StartupPhase.SCHEDULER, startup_dependency_policy=StartupDependencyPolicy.OPTIONAL_AFTER_READY, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.SCHEDULED_ONLY, failure_policy=ServiceFailurePolicy.DISABLE_OPTIONAL_FEATURE, enabled_by_default=False, explanation_nl="Deze toekomstige service plant veilige jobs in vaste intervallen."),
        RuntimeServiceDefinition(runtime_service_id="svc_data_updater", service_kind=RuntimeServiceKind.DATA_SOURCE_UPDATER, service_name="Data bijwerken", criticality=RuntimeServiceCriticality.FUTURE, startup_phase=StartupPhase.BACKGROUND_JOBS, startup_dependency_policy=StartupDependencyPolicy.OPTIONAL_AFTER_READY, resource_profile=RuntimeResourceProfile.MODERATE, parallel_execution_policy=ParallelExecutionPolicy.QUEUE_REQUIRED, failure_policy=ServiceFailurePolicy.BLOCK_SUGGESTIONS, enabled_by_default=False, explanation_nl="Deze toekomstige service ververst databronnen via gecontroleerde taken."),
        RuntimeServiceDefinition(runtime_service_id="svc_research_worker", service_kind=RuntimeServiceKind.RESEARCH_WORKER, service_name="Onderzoek worker", criticality=RuntimeServiceCriticality.FUTURE, startup_phase=StartupPhase.BACKGROUND_JOBS, startup_dependency_policy=StartupDependencyPolicy.OPTIONAL_AFTER_READY, resource_profile=RuntimeResourceProfile.HEAVY, parallel_execution_policy=ParallelExecutionPolicy.EXTERNAL_WORKER_RECOMMENDED, failure_policy=ServiceFailurePolicy.DISABLE_OPTIONAL_FEATURE, enabled_by_default=False, explanation_nl="Deze toekomstige service voert zwaar onderzoek uit via queue op sterkere machine."),
        RuntimeServiceDefinition(runtime_service_id="svc_ai_queue", service_kind=RuntimeServiceKind.AI_RESEARCH_QUEUE, service_name="AI onderzoek queue", criticality=RuntimeServiceCriticality.FUTURE, startup_phase=StartupPhase.BACKGROUND_JOBS, startup_dependency_policy=StartupDependencyPolicy.OPTIONAL_AFTER_READY, resource_profile=RuntimeResourceProfile.MODERATE, parallel_execution_policy=ParallelExecutionPolicy.QUEUE_REQUIRED, failure_policy=ServiceFailurePolicy.DISABLE_OPTIONAL_FEATURE, enabled_by_default=False, explanation_nl="Deze toekomstige service beheert AI onderzoekstaken in een controleerbare wachtrij."),
        RuntimeServiceDefinition(runtime_service_id="svc_ibkr", service_kind=RuntimeServiceKind.IBKR_ADAPTER, service_name="IBKR adapter", criticality=RuntimeServiceCriticality.FUTURE, startup_phase=StartupPhase.ADAPTERS, startup_dependency_policy=StartupDependencyPolicy.OPTIONAL_AFTER_READY, resource_profile=RuntimeResourceProfile.MODERATE, parallel_execution_policy=ParallelExecutionPolicy.SCHEDULED_ONLY, failure_policy=ServiceFailurePolicy.ALLOW_EXISTING_DATA_WITH_WARNING, enabled_by_default=False, explanation_nl="Deze toekomstige service controleert IBKR paper-status zonder live uitvoering."),
        RuntimeServiceDefinition(runtime_service_id="svc_backup", service_kind=RuntimeServiceKind.BACKUP_SERVICE, service_name="Backup service", criticality=RuntimeServiceCriticality.FUTURE, startup_phase=StartupPhase.MONITORING, startup_dependency_policy=StartupDependencyPolicy.OPTIONAL_AFTER_READY, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.SCHEDULED_ONLY, failure_policy=ServiceFailurePolicy.MANUAL_INTERVENTION_REQUIRED, enabled_by_default=False, explanation_nl="Deze toekomstige service bewaakt backups en herstelcontroles."),
        RuntimeServiceDefinition(runtime_service_id="svc_proxy", service_kind=RuntimeServiceKind.REVERSE_PROXY, service_name="Reverse proxy", criticality=RuntimeServiceCriticality.OPTIONAL, startup_phase=StartupPhase.READY, startup_dependency_policy=StartupDependencyPolicy.INDEPENDENT, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.PARALLEL_SAFE, failure_policy=ServiceFailurePolicy.DISABLE_OPTIONAL_FEATURE, enabled_by_default=False, explanation_nl="Deze optionele service regelt netwerktoegang voor lokale clients."),
    ]
    steps = [
        StartupPlanStep(step_order=i + 1, startup_phase=s.startup_phase, runtime_service_id=s.runtime_service_id, required=s.criticality is RuntimeServiceCriticality.REQUIRED, explanation_nl=f"Start {s.service_name.lower()} in fase {s.startup_phase.value}.")
        for i, s in enumerate(services)
    ]
    return RuntimeTopology(
        runtime_topology_id="topology_default",
        topology_name="Default runtime topology",
        target=RuntimeDeploymentTarget.RASPBERRY_PI_5,
        services=services,
        startup_plan=StartupPlan(
            startup_plan_id="startup_default",
            plan_name="Standaard opstartplan",
            target=RuntimeDeploymentTarget.RASPBERRY_PI_5,
            steps=steps,
            created_at=created_at,
        ),
        created_at=created_at,
    )


def build_default_background_job_types() -> list[BackgroundJobType]:
    return [
        BackgroundJobType(background_job_type_id="job_portfolio_review", job_name="Portfolio review", service_kind=RuntimeServiceKind.WORKER, resource_profile=RuntimeResourceProfile.MODERATE, parallel_execution_policy=ParallelExecutionPolicy.SCHEDULED_ONLY, allowed_on_raspberry_pi_5=True, requires_queue=False, explanation_nl="Periodieke controle van portefeuilledata zonder uitvoering."),
        BackgroundJobType(background_job_type_id="job_data_source_refresh", job_name="Data source refresh", service_kind=RuntimeServiceKind.DATA_SOURCE_UPDATER, resource_profile=RuntimeResourceProfile.MODERATE, parallel_execution_policy=ParallelExecutionPolicy.QUEUE_REQUIRED, allowed_on_raspberry_pi_5=True, requires_queue=True, explanation_nl="Ververs databronnen via queue met zichtbare status."),
        BackgroundJobType(background_job_type_id="job_ibkr_paper_status_check", job_name="IBKR paper status check", service_kind=RuntimeServiceKind.IBKR_ADAPTER, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.SCHEDULED_ONLY, allowed_on_raspberry_pi_5=True, requires_queue=False, explanation_nl="Controleer alleen paper-verbinding en rechten."),
        BackgroundJobType(background_job_type_id="job_ai_research_run", job_name="AI research run", service_kind=RuntimeServiceKind.RESEARCH_WORKER, resource_profile=RuntimeResourceProfile.HEAVY, parallel_execution_policy=ParallelExecutionPolicy.QUEUE_REQUIRED, allowed_on_raspberry_pi_5=False, requires_queue=True, explanation_nl="AI onderzoek via queue en audit, zonder trade-uitvoering."),
        BackgroundJobType(background_job_type_id="job_suggestion_generation", job_name="Suggestion generation", service_kind=RuntimeServiceKind.WORKER, resource_profile=RuntimeResourceProfile.MODERATE, parallel_execution_policy=ParallelExecutionPolicy.QUEUE_REQUIRED, allowed_on_raspberry_pi_5=True, requires_queue=True, explanation_nl="Genereer suggesties alleen na data-kwaliteitscontrole."),
        BackgroundJobType(background_job_type_id="job_data_quality_check", job_name="Data quality check", service_kind=RuntimeServiceKind.HEALTH_MONITOR, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.SCHEDULED_ONLY, allowed_on_raspberry_pi_5=True, requires_queue=False, explanation_nl="Controle op volledigheid, versheid en fouten in data."),
        BackgroundJobType(background_job_type_id="job_audit_maintenance", job_name="Audit maintenance", service_kind=RuntimeServiceKind.AUDIT_LOGGER, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.SCHEDULED_ONLY, allowed_on_raspberry_pi_5=True, requires_queue=False, explanation_nl="Onderhoud auditlog en controle op ontbrekende events."),
        BackgroundJobType(background_job_type_id="job_backup_check", job_name="Backup check", service_kind=RuntimeServiceKind.BACKUP_SERVICE, resource_profile=RuntimeResourceProfile.LIGHTWEIGHT, parallel_execution_policy=ParallelExecutionPolicy.SCHEDULED_ONLY, allowed_on_raspberry_pi_5=True, requires_queue=False, explanation_nl="Controleer geplande backup en herstelteststatus."),
    ]


def find_service(topology: RuntimeTopology, service_kind: RuntimeServiceKind) -> RuntimeServiceDefinition | None:
    for service in topology.services:
        if service.service_kind is service_kind:
            return service
    return None


def service_blocks_suggestions(service: RuntimeServiceDefinition, health: RuntimeServiceHealth) -> bool:
    if health.blocks_new_suggestions:
        return True
    if health.severity is RuntimeHealthSeverity.CRITICAL:
        return True
    if (
        service.criticality is RuntimeServiceCriticality.OPTIONAL
        and service.failure_policy is ServiceFailurePolicy.DISABLE_OPTIONAL_FEATURE
    ):
        return False
    return (
        service.failure_policy is ServiceFailurePolicy.BLOCK_SUGGESTIONS
        and health.status
        in {
            RuntimeServiceStatus.DEGRADED,
            RuntimeServiceStatus.UNHEALTHY,
            RuntimeServiceStatus.STOPPED,
            RuntimeServiceStatus.BLOCKED,
        }
    )


def required_services(topology: RuntimeTopology) -> list[RuntimeServiceDefinition]:
    return [s for s in topology.services if s.criticality is RuntimeServiceCriticality.REQUIRED]


def parallel_safe_services(topology: RuntimeTopology) -> list[RuntimeServiceDefinition]:
    return [
        s
        for s in topology.services
        if s.parallel_execution_policy is ParallelExecutionPolicy.PARALLEL_SAFE
        and s.resource_profile is not RuntimeResourceProfile.HEAVY
    ]
