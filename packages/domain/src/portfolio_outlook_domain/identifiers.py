from typing import Annotated

from pydantic import StringConstraints

SafeIdentifier = Annotated[
    str,
    StringConstraints(min_length=1, pattern=r"^[A-Za-z0-9_-]+$"),
]

PortfolioId = SafeIdentifier
InstrumentId = SafeIdentifier
TransactionId = SafeIdentifier
LotId = SafeIdentifier
SuggestionId = SafeIdentifier
RunId = SafeIdentifier
SourceId = SafeIdentifier
AuditEventId = SafeIdentifier

OrderId = SafeIdentifier
FillId = SafeIdentifier
LedgerEntryId = SafeIdentifier
CostEstimateId = SafeIdentifier
CorporateActionId = SafeIdentifier
FifoAllocationId = SafeIdentifier

TermDepositId = SafeIdentifier


ApprovalRequestId = SafeIdentifier
ApprovalDecisionId = SafeIdentifier
ExecutionIntentId = SafeIdentifier
ExecutionTargetId = SafeIdentifier
BrokerReferenceId = SafeIdentifier
BrokerOrderReferenceId = SafeIdentifier
ResearchRunId = SafeIdentifier
ResearchReportId = SafeIdentifier
SourceReferenceId = SafeIdentifier
RawDataArchiveId = SafeIdentifier
ResearchArchiveId = SafeIdentifier

DataSourceId = SafeIdentifier
DataSourcePolicyId = SafeIdentifier
DataSourceRequirementId = SafeIdentifier
DataSourceRegistryId = SafeIdentifier

RuntimeServiceId = SafeIdentifier
RuntimeTopologyId = SafeIdentifier
StartupPlanId = SafeIdentifier
HealthCheckId = SafeIdentifier
BackgroundJobTypeId = SafeIdentifier
SchedulerPlanId = SafeIdentifier
ScheduledJobId = SafeIdentifier
JobRunId = SafeIdentifier
RetryPolicyId = SafeIdentifier
JobEligibilityCheckId = SafeIdentifier

DataQualityGateId = SafeIdentifier
SuggestionEligibilityCheckId = SafeIdentifier
SuggestionEligibilityPolicyId = SafeIdentifier
DataFreshnessCheckId = SafeIdentifier
