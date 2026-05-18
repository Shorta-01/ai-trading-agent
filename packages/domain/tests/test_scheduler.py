from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel, ValidationError

from portfolio_outlook_domain.enums import (
    DataDomain,
    JobBlockReason,
    JobPriority,
    JobResourceLimit,
    JobSafetyImpact,
    RetryBackoffPolicy,
    RuntimeDeploymentTarget,
    ScheduleCadence,
    ScheduledJobStatus,
)
from portfolio_outlook_domain.identifiers import JobRunId, ScheduledJobId, SchedulerPlanId
from portfolio_outlook_domain.scheduler import (
    JobRunRecord,
    RetryPolicy,
    ScheduledJobDefinition,
    SchedulerPlan,
    build_blocked_eligibility_check,
    build_default_scheduler_plan,
    build_eligible_check,
    job_allowed_on_raspberry_pi,
    job_can_create_suggestions,
    job_requires_queue,
)


class _SchedulerPlanIdModel(BaseModel):
    value: SchedulerPlanId


class _ScheduledJobIdModel(BaseModel):
    value: ScheduledJobId


class _JobRunIdModel(BaseModel):
    value: JobRunId


def _retry_none() -> RetryPolicy:
    return RetryPolicy(
        retry_policy_id="retry_none",
        backoff_policy=RetryBackoffPolicy.NONE,
        max_attempts=0,
        delay_seconds=0,
        explanation_nl="Geen retry",
    )


def _job() -> ScheduledJobDefinition:
    return ScheduledJobDefinition(
        scheduled_job_id="sched_test",
        background_job_type_id="job_test",
        job_name="Test job",
        cadence=ScheduleCadence.HOURLY,
        priority=JobPriority.NORMAL,
        safety_impact=JobSafetyImpact.READ_ONLY,
        resource_limit=JobResourceLimit.RASPBERRY_PI_SAFE,
        required_service_ids=["svc_worker"],
        required_data_domains=[DataDomain.MARKET_DATA],
        retry_policy=_retry_none(),
        enabled_by_default=True,
        explanation_nl="Korte uitleg",
    )


def test_identifiers() -> None:
    assert _SchedulerPlanIdModel(value="plan_1").value == "plan_1"
    assert _ScheduledJobIdModel(value="sched_1").value == "sched_1"
    assert _JobRunIdModel(value="run_1").value == "run_1"
    with pytest.raises(ValidationError):
        _ScheduledJobIdModel(value="")


def test_retry_policy_rules() -> None:
    assert _retry_none().model_dump()["max_attempts"] == 0
    with pytest.raises(ValidationError):
        RetryPolicy(
            retry_policy_id="x",
            backoff_policy=RetryBackoffPolicy.NONE,
            max_attempts=1,
            delay_seconds=0,
            explanation_nl="x",
        )
    with pytest.raises(ValidationError):
        RetryPolicy(
            retry_policy_id="x",
            backoff_policy=RetryBackoffPolicy.NONE,
            max_attempts=0,
            delay_seconds=1,
            explanation_nl="x",
        )


def test_job_and_helpers() -> None:
    job = _job()
    assert job.model_dump()["job_name"] == "Test job"
    assert job_can_create_suggestions(job) is False
    assert job_requires_queue(job) is False
    assert job_allowed_on_raspberry_pi(job) is True


def test_plan_and_records() -> None:
    now = datetime.now(tz=UTC)
    plan = SchedulerPlan(
        scheduler_plan_id="plan_1",
        plan_name="Plan",
        target=RuntimeDeploymentTarget.RASPBERRY_PI_5,
        jobs=[_job()],
        created_at=now,
    )
    assert plan.model_dump()["plan_name"] == "Plan"

    elig = build_eligible_check(job=_job(), checked_at=now, explanation_nl="ok")
    assert elig.status is ScheduledJobStatus.ELIGIBLE

    blocked = build_blocked_eligibility_check(
        job=_job(),
        checked_at=now,
        block_reasons=[JobBlockReason.DATA_QUALITY_FAILED],
        explanation_nl="blocked",
    )
    assert blocked.status is ScheduledJobStatus.BLOCKED

    running = JobRunRecord(
        job_run_id="run1",
        scheduled_job_id="sched_test",
        status=ScheduledJobStatus.RUNNING,
        started_at=now,
        attempt_number=1,
        message_nl="Bezig",
    )
    assert running.model_dump()["attempt_number"] == 1

    with pytest.raises(ValidationError):
        JobRunRecord(
            job_run_id="run2",
            scheduled_job_id="sched_test",
            status=ScheduledJobStatus.COMPLETED,
            started_at=now,
            finished_at=now - timedelta(minutes=1),
            attempt_number=1,
            message_nl="Fout tijd",
        )


def test_default_plan() -> None:
    plan = build_default_scheduler_plan(created_at=datetime.now(tz=UTC))
    names = {job.job_name.lower() for job in plan.jobs}
    assert "portfolio review" in names
    assert "data source refresh" in names
    assert "ibkr paper status check" in names
    assert "ai research run" in names
    assert "suggestion generation" in names
    assert "data quality check" in names
    assert "audit maintenance" in names
    assert "backup check" in names
