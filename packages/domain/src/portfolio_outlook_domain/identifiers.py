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
