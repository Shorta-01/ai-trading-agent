from datetime import UTC, datetime

from pydantic import Field, model_validator

from .enums import (
    DataDomain,
    DataQualityStatus,
    JobBlockReason,
    JobPriority,
    JobResourceLimit,
    JobSafetyImpact,
    JobSkipReason,
    RetryBackoffPolicy,
    RuntimeDeploymentTarget,
    ScheduleCadence,
    ScheduledJobStatus,
)
from .identifiers import (
    AuditEventId,
    BackgroundJobTypeId,
    HealthCheckId,
    JobEligibilityCheckId,
    JobRunId,
    RetryPolicyId,
    RuntimeServiceId,
    ScheduledJobId,
    SchedulerPlanId,
    SourceReferenceId,
)
from .primitives import DomainBaseModel


class RetryPolicy(DomainBaseModel):
    retry_policy_id: RetryPolicyId
    backoff_policy: RetryBackoffPolicy
    max_attempts: int = Field(ge=0)
    delay_seconds: int = Field(ge=0)
    explanation_nl: str

    @model_validator(mode="after")
    def validate_model(self) -> "RetryPolicy":
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl is verplicht")
        if self.backoff_policy is RetryBackoffPolicy.NONE:
            if self.max_attempts != 0 or self.delay_seconds != 0:
                raise ValueError("none policy vereist max_attempts=0 en delay_seconds=0")
        if self.backoff_policy is RetryBackoffPolicy.MANUAL_ONLY and self.max_attempts != 0:
            raise ValueError("manual_only policy vereist max_attempts=0")
        return self


class ScheduledJobDefinition(DomainBaseModel):
    scheduled_job_id: ScheduledJobId
    background_job_type_id: BackgroundJobTypeId
    job_name: str
    cadence: ScheduleCadence
    priority: JobPriority
    safety_impact: JobSafetyImpact
    resource_limit: JobResourceLimit
    required_service_ids: list[RuntimeServiceId] = Field(default_factory=list)
    required_data_domains: list[DataDomain] = Field(default_factory=list)
    retry_policy: RetryPolicy
    enabled_by_default: bool
    explanation_nl: str

    @model_validator(mode="after")
    def validate_model(self) -> "ScheduledJobDefinition":
        if not self.job_name.strip() or not self.explanation_nl.strip():
            raise ValueError("job_name en explanation_nl zijn verplicht")
        if self.cadence is ScheduleCadence.DISABLED and self.enabled_by_default:
            raise ValueError("disabled cadence vereist enabled_by_default=False")
        if self.safety_impact is JobSafetyImpact.MAY_CREATE_SUGGESTIONS:
            if not self.required_service_ids:
                raise ValueError("suggestie-jobs vereisen required_service_ids")
            if not self.required_data_domains:
                raise ValueError("suggestie-jobs vereisen required_data_domains")
        if (
            self.resource_limit is JobResourceLimit.EXTERNAL_WORKER_RECOMMENDED
            and self.cadence is ScheduleCadence.EVERY_5_MINUTES
        ):
            raise ValueError("external_worker_recommended mag niet every_5_minutes zijn")
        if (
            self.resource_limit is JobResourceLimit.BLOCKED_ON_RASPBERRY_PI
            and self.enabled_by_default
        ):
            raise ValueError("blocked_on_raspberry_pi vereist enabled_by_default=False")
        return self


class JobEligibilityCheck(DomainBaseModel):
    job_eligibility_check_id: JobEligibilityCheckId
    scheduled_job_id: ScheduledJobId
    checked_at: datetime
    status: ScheduledJobStatus
    skip_reasons: list[JobSkipReason] = Field(default_factory=list)
    block_reasons: list[JobBlockReason] = Field(default_factory=list)
    service_health_ids: list[HealthCheckId] = Field(default_factory=list)
    source_reference_ids: list[SourceReferenceId] = Field(default_factory=list)
    data_quality_status: DataQualityStatus
    explanation_nl: str

    @model_validator(mode="after")
    def validate_model(self) -> "JobEligibilityCheck":
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl is verplicht")
        if self.status is ScheduledJobStatus.ELIGIBLE:
            if self.skip_reasons or self.block_reasons:
                raise ValueError("eligible status mag geen skip/block redenen hebben")
        if self.block_reasons and self.status is not ScheduledJobStatus.BLOCKED:
            raise ValueError("block_reasons vereisen blocked status")
        if (
            self.skip_reasons
            and not self.block_reasons
            and self.status is not ScheduledJobStatus.SKIPPED
        ):
            raise ValueError("skip_reasons vereisen skipped status")
        return self


class JobRunRecord(DomainBaseModel):
    job_run_id: JobRunId
    scheduled_job_id: ScheduledJobId
    status: ScheduledJobStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    attempt_number: int = Field(ge=1)
    eligibility_check_id: JobEligibilityCheckId | None = None
    audit_event_ids: list[AuditEventId] = Field(default_factory=list)
    message_nl: str

    @model_validator(mode="after")
    def validate_model(self) -> "JobRunRecord":
        if not self.message_nl.strip():
            raise ValueError("message_nl is verplicht")
        if self.status is ScheduledJobStatus.RUNNING:
            if self.started_at is None or self.finished_at is not None:
                raise ValueError("running vereist started_at en geen finished_at")
        if self.status in {ScheduledJobStatus.COMPLETED, ScheduledJobStatus.FAILED}:
            if self.started_at is None or self.finished_at is None:
                raise ValueError("completed/failed vereist started_at en finished_at")
            if self.finished_at < self.started_at:
                raise ValueError("finished_at moet na started_at liggen")
        if (
            self.status in {ScheduledJobStatus.BLOCKED, ScheduledJobStatus.SKIPPED}
            and self.eligibility_check_id is None
        ):
            raise ValueError("blocked/skipped moet eligibility_check_id bevatten")
        return self


class SchedulerPlan(DomainBaseModel):
    scheduler_plan_id: SchedulerPlanId
    plan_name: str
    target: RuntimeDeploymentTarget
    jobs: list[ScheduledJobDefinition]
    created_at: datetime

    @model_validator(mode="after")
    def validate_model(self) -> "SchedulerPlan":
        if not self.plan_name.strip():
            raise ValueError("plan_name is verplicht")
        if not self.jobs:
            raise ValueError("jobs mogen niet leeg zijn")
        ids = [job.scheduled_job_id for job in self.jobs]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate scheduled_job_id")
        return self


def _default_retry_none() -> RetryPolicy:
    return RetryPolicy(
        retry_policy_id="retry_none",
        backoff_policy=RetryBackoffPolicy.NONE,
        max_attempts=0,
        delay_seconds=0,
        explanation_nl="Geen herhaling; alleen nieuwe planning.",
    )


def _default_retry_exp() -> RetryPolicy:
    return RetryPolicy(
        retry_policy_id="retry_exp_3",
        backoff_policy=RetryBackoffPolicy.EXPONENTIAL,
        max_attempts=3,
        delay_seconds=300,
        explanation_nl="Bij fout opnieuw proberen met oplopende wachttijd.",
    )


def build_default_scheduler_plan(*, created_at: datetime) -> SchedulerPlan:
    jobs = [
        ScheduledJobDefinition(
            scheduled_job_id="sched_portfolio_review",
            background_job_type_id="job_portfolio_review",
            job_name="Portfolio review",
            cadence=ScheduleCadence.HOURLY,
            priority=JobPriority.NORMAL,
            safety_impact=JobSafetyImpact.MAY_UPDATE_PORTFOLIO_STATE,
            resource_limit=JobResourceLimit.RASPBERRY_PI_SAFE,
            required_service_ids=["svc_worker", "svc_audit"],
            required_data_domains=[DataDomain.PORTFOLIO_ANALYTICS],
            retry_policy=_default_retry_exp(),
            enabled_by_default=True,
            explanation_nl=(
                "Controleert periodiek de portefeuillestatus zonder orders uit te voeren."
            ),
        ),
        ScheduledJobDefinition(
            scheduled_job_id="sched_data_source_refresh",
            background_job_type_id="job_data_source_refresh",
            job_name="Data source refresh",
            cadence=ScheduleCadence.HOURLY,
            priority=JobPriority.NORMAL,
            safety_impact=JobSafetyImpact.MAY_UPDATE_RESEARCH,
            resource_limit=JobResourceLimit.QUEUE_REQUIRED,
            required_service_ids=["svc_worker"],
            required_data_domains=[DataDomain.MARKET_DATA],
            retry_policy=_default_retry_exp(),
            enabled_by_default=True,
            explanation_nl="Vernieuwt databronnen volgens schema met beperkte belasting.",
        ),
        ScheduledJobDefinition(
            scheduled_job_id="sched_ibkr_paper_status_check",
            background_job_type_id="job_ibkr_paper_status_check",
            job_name="IBKR paper status check",
            cadence=ScheduleCadence.DAILY,
            priority=JobPriority.HIGH,
            safety_impact=JobSafetyImpact.READ_ONLY,
            resource_limit=JobResourceLimit.RASPBERRY_PI_SAFE,
            required_service_ids=["svc_health"],
            required_data_domains=[DataDomain.ORDER_EXECUTION],
            retry_policy=_default_retry_none(),
            enabled_by_default=False,
            explanation_nl="Controleert later de paper-koppeling, zonder live uitvoering.",
        ),
        ScheduledJobDefinition(
            scheduled_job_id="sched_ai_research_run",
            background_job_type_id="job_ai_research_run",
            job_name="AI research run",
            cadence=ScheduleCadence.DAILY,
            priority=JobPriority.LOW,
            safety_impact=JobSafetyImpact.MAY_UPDATE_RESEARCH,
            resource_limit=JobResourceLimit.EXTERNAL_WORKER_RECOMMENDED,
            required_service_ids=["svc_worker", "svc_audit"],
            required_data_domains=[DataDomain.NEWS_SIGNAL],
            retry_policy=_default_retry_exp(),
            enabled_by_default=False,
            explanation_nl="Plant AI-onderzoek als wachtrijtaak met volledige audit.",
        ),
        ScheduledJobDefinition(
            scheduled_job_id="sched_suggestion_generation",
            background_job_type_id="job_suggestion_generation",
            job_name="Suggestion generation",
            cadence=ScheduleCadence.HOURLY,
            priority=JobPriority.CRITICAL,
            safety_impact=JobSafetyImpact.MAY_CREATE_SUGGESTIONS,
            resource_limit=JobResourceLimit.QUEUE_REQUIRED,
            required_service_ids=["svc_worker", "svc_health", "svc_audit"],
            required_data_domains=[DataDomain.MARKET_DATA, DataDomain.PORTFOLIO_ANALYTICS],
            retry_policy=_default_retry_exp(),
            enabled_by_default=True,
            explanation_nl="Maakt alleen suggesties met verse data en gezonde services.",
        ),
        ScheduledJobDefinition(
            scheduled_job_id="sched_data_quality_check",
            background_job_type_id="job_data_quality_check",
            job_name="Data quality check",
            cadence=ScheduleCadence.EVERY_15_MINUTES,
            priority=JobPriority.HIGH,
            safety_impact=JobSafetyImpact.AUDIT_ONLY,
            resource_limit=JobResourceLimit.RASPBERRY_PI_SAFE,
            required_service_ids=["svc_health", "svc_audit"],
            required_data_domains=[DataDomain.MARKET_DATA],
            retry_policy=_default_retry_exp(),
            enabled_by_default=True,
            explanation_nl="Controleert datakwaliteit zodat geen verouderde adviezen ontstaan.",
        ),
        ScheduledJobDefinition(
            scheduled_job_id="sched_audit_maintenance",
            background_job_type_id="job_audit_maintenance",
            job_name="Audit maintenance",
            cadence=ScheduleCadence.DAILY,
            priority=JobPriority.NORMAL,
            safety_impact=JobSafetyImpact.AUDIT_ONLY,
            resource_limit=JobResourceLimit.RASPBERRY_PI_SAFE,
            required_service_ids=["svc_audit"],
            required_data_domains=[DataDomain.AUDIT_LOG],
            retry_policy=_default_retry_exp(),
            enabled_by_default=True,
            explanation_nl="Houdt auditsporen compleet en controleerbaar.",
        ),
        ScheduledJobDefinition(
            scheduled_job_id="sched_backup_check",
            background_job_type_id="job_backup_check",
            job_name="Backup check",
            cadence=ScheduleCadence.DAILY,
            priority=JobPriority.HIGH,
            safety_impact=JobSafetyImpact.AUDIT_ONLY,
            resource_limit=JobResourceLimit.RASPBERRY_PI_SAFE,
            required_service_ids=["svc_backup", "svc_audit"],
            required_data_domains=[DataDomain.AUDIT_LOG],
            retry_policy=_default_retry_exp(),
            enabled_by_default=True,
            explanation_nl="Controleert of backups aanwezig en verifieerbaar zijn.",
        ),
    ]
    return SchedulerPlan(
        scheduler_plan_id="scheduler_plan_default",
        plan_name="Standaard planning",
        target=RuntimeDeploymentTarget.RASPBERRY_PI_5,
        jobs=jobs,
        created_at=created_at.astimezone(UTC),
    )


def job_can_create_suggestions(job: ScheduledJobDefinition) -> bool:
    return job.safety_impact is JobSafetyImpact.MAY_CREATE_SUGGESTIONS


def job_requires_queue(job: ScheduledJobDefinition) -> bool:
    return (
        job.resource_limit
        in {JobResourceLimit.QUEUE_REQUIRED, JobResourceLimit.EXTERNAL_WORKER_RECOMMENDED}
        or job.safety_impact is JobSafetyImpact.MAY_CREATE_SUGGESTIONS
    )


def job_allowed_on_raspberry_pi(job: ScheduledJobDefinition) -> bool:
    if job.resource_limit is JobResourceLimit.BLOCKED_ON_RASPBERRY_PI:
        return False
    if (
        job.resource_limit is JobResourceLimit.EXTERNAL_WORKER_RECOMMENDED
        and job.enabled_by_default
    ):
        return False
    return True


def build_blocked_eligibility_check(
    *,
    job: ScheduledJobDefinition,
    checked_at: datetime,
    block_reasons: list[JobBlockReason],
    explanation_nl: str,
) -> JobEligibilityCheck:
    if not block_reasons:
        raise ValueError("block_reasons mogen niet leeg zijn")
    return JobEligibilityCheck(
        job_eligibility_check_id=f"elig_{job.scheduled_job_id}_blocked",
        scheduled_job_id=job.scheduled_job_id,
        checked_at=checked_at,
        status=ScheduledJobStatus.BLOCKED,
        block_reasons=block_reasons,
        data_quality_status=DataQualityStatus.FAILED,
        explanation_nl=explanation_nl,
    )


def build_eligible_check(
    *,
    job: ScheduledJobDefinition,
    checked_at: datetime,
    explanation_nl: str,
) -> JobEligibilityCheck:
    return JobEligibilityCheck(
        job_eligibility_check_id=f"elig_{job.scheduled_job_id}_ok",
        scheduled_job_id=job.scheduled_job_id,
        checked_at=checked_at,
        status=ScheduledJobStatus.ELIGIBLE,
        data_quality_status=DataQualityStatus.OK,
        explanation_nl=explanation_nl,
    )
