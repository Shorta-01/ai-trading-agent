"""Typed read-only market-data readiness response contracts and builders."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel


class ReadinessWatchlistItemLike(Protocol):
    watchlist_item_id: str
    asset_id: str | None
    ibkr_conid: str | None
    symbol: str
    ibkr_validation_status: str | None


class ReadinessValidationStatus(BaseModel):
    ibkr_conid_present: bool
    ibkr_contract_validated: bool


class ReadinessAssetListingGateStatus(StrEnum):
    STORAGE_UNAVAILABLE = "storage_unavailable"
    MISSING_IBKR_CONID = "missing_ibkr_conid"
    MISSING_LISTING = "missing_listing"
    UNVALIDATED_LISTING = "unvalidated_listing"
    VALIDATED_LISTING = "validated_listing"


class ReadinessAssetListingGate(BaseModel):
    status: ReadinessAssetListingGateStatus
    listing_id: str | None
    asset_id: str | None
    ibkr_conid: str | None
    validation_status: str | None
    safe_to_use_for_market_data: bool
    blocks_market_data: bool
    status_nl: str
    next_step_nl: str
    audit_help_nl: str


class ReadinessStatus(StrEnum):
    BLOCKED = "blocked"
    READY = "ready"


class ReadinessFreshnessStatus(StrEnum):
    MISSING_SNAPSHOT = "missing_snapshot"
    SNAPSHOT_AVAILABLE = "snapshot_available"


class ReadinessBlockerCode(StrEnum):
    MISSING_OR_UNVALIDATED_IBKR_CONTRACT = "missing_or_unvalidated_ibkr_contract"


class LatestSnapshotStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    MISSING_SNAPSHOT = "missing_snapshot"
    SNAPSHOT_AVAILABLE = "snapshot_available"
    STORAGE_FAILURE = "storage_failure"


class ReadinessSnapshotMetadata(BaseModel):
    snapshot_id: str
    watchlist_item_id: str
    asset_id: str | None
    ibkr_conid: str
    symbol: str
    security_type: str
    exchange: str | None
    primary_exchange: str | None
    currency: str
    provider_name: str
    data_kind: str
    captured_at: datetime
    source_timestamp: datetime | None
    stored_at: datetime
    freshness_status: str
    validation_status: str
    blocked_reason: str | None
    raw_reference: str | None
    explanation_nl: str


READINESS_HELP_NL = (
    "Read-only readinessstatus: geen market-data fetch, geen analyse, geen suggesties, "
    "geen Decision Packages, geen actiedrafts en geen orders."
)

READINESS_AUDIT_HELP_NL = (
    "Dit is read-only status/auditinformatie: geen market-data runtime, geen runtime-fetch, "
    "geen analysevrijgave, geen suggesties en geen acties/orders."
)


class ReadinessRow(BaseModel):
    watchlist_item_id: str
    asset_id: str | None
    ibkr_conid: str | None
    symbol: str
    readiness_status: ReadinessStatus
    status: ReadinessStatus
    freshness_status: ReadinessFreshnessStatus
    blocker_code: ReadinessBlockerCode | None
    blocker_reason_nl: str
    required_identity_fields: list[str]
    missing_identity_fields: list[str]
    validation_status: ReadinessValidationStatus
    asset_listing_gate: ReadinessAssetListingGate
    evaluated_at: str
    latest_snapshot_metadata: ReadinessSnapshotMetadata | None
    snapshot_metadata_present: bool
    next_step_nl: str
    audit_help_nl: str
    help_nl: str
    analysis_ready: bool
    suggestions_allowed: bool
    action_drafts_allowed: bool


class ReadinessListResponse(BaseModel):
    items: list[ReadinessRow]
    help_nl: str
    analysis_ready: bool
    suggestions_allowed: bool
    action_drafts_allowed: bool


class ReadinessDetailResponse(BaseModel):
    item: ReadinessRow | None
    message_nl: str | None = None


class LatestSnapshotResponse(BaseModel):
    ibkr_conid: str
    status: LatestSnapshotStatus
    status_nl: str
    latest_snapshot_metadata: ReadinessSnapshotMetadata | None
    evaluated_at: str
    missing_reason: str | None = None
    blocker_reason: str | None = None
    next_step_nl: str
    help_nl: str
    analysis_ready: bool
    suggestions_allowed: bool
    action_drafts_allowed: bool


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_readiness_row(
    item: ReadinessWatchlistItemLike,
    snapshot_metadata: ReadinessSnapshotMetadata | None,
    asset_listing_gate: ReadinessAssetListingGate,
    *,
    evaluated_at: str,
) -> ReadinessRow:
    conid = (item.ibkr_conid or "").strip()
    conid_present = bool(conid)
    validation_ok = item.ibkr_validation_status == "valid"
    ready = validation_ok and conid_present
    freshness_status = (
        ReadinessFreshnessStatus.SNAPSHOT_AVAILABLE
        if snapshot_metadata
        else ReadinessFreshnessStatus.MISSING_SNAPSHOT
    )
    status = ReadinessStatus.READY if ready else ReadinessStatus.BLOCKED
    blocker_code = (
        None if ready else ReadinessBlockerCode.MISSING_OR_UNVALIDATED_IBKR_CONTRACT
    )

    missing_identity_fields: list[str] = []
    if not conid_present:
        missing_identity_fields.append("ibkr_conid")
    if not validation_ok:
        missing_identity_fields.append("ibkr_validation_status_valid")

    blocker_reason_nl = (
        "Klaar voor latere market-data opslag op identiteitsniveau."
        if ready
        else (
            "Geblokkeerd: gevalideerde IBKR-contractidentiteit ontbreekt of is ongeldig. "
            "Market data, analyse, suggesties en actiedrafts blijven niet toegestaan."
        )
    )
    next_step_nl = (
        "Controleer de opgeslagen snapshotmetadata; dit blijft read-only statusinformatie."
        if snapshot_metadata
        else (
            "Koppel of valideer eerst het juiste IBKR-contract (conid)."
            if not ready
            else "Wacht op toekomstige opslag van een eerste market-data snapshot."
        )
    )

    return ReadinessRow(
        watchlist_item_id=item.watchlist_item_id,
        asset_id=item.asset_id,
        ibkr_conid=item.ibkr_conid,
        symbol=item.symbol,
        readiness_status=status,
        status=status,
        freshness_status=freshness_status,
        blocker_code=blocker_code,
        blocker_reason_nl=blocker_reason_nl,
        required_identity_fields=["ibkr_conid", "ibkr_validation_status_valid"],
        missing_identity_fields=missing_identity_fields,
        validation_status=ReadinessValidationStatus(
            ibkr_conid_present=conid_present,
            ibkr_contract_validated=validation_ok,
        ),
        asset_listing_gate=asset_listing_gate,
        evaluated_at=evaluated_at,
        latest_snapshot_metadata=snapshot_metadata,
        snapshot_metadata_present=snapshot_metadata is not None,
        next_step_nl=next_step_nl,
        audit_help_nl=READINESS_AUDIT_HELP_NL,
        help_nl=READINESS_HELP_NL,
        analysis_ready=False,
        suggestions_allowed=False,
        action_drafts_allowed=False,
    )


def build_readiness_snapshot_metadata(record: object) -> ReadinessSnapshotMetadata:
    """Build typed snapshot metadata from repository records or attribute-based test doubles."""

    return ReadinessSnapshotMetadata.model_validate(record, from_attributes=True)


def build_latest_snapshot_response(
    ibkr_conid: str,
    latest_snapshot_metadata: ReadinessSnapshotMetadata | None,
    *,
    status: LatestSnapshotStatus,
    status_nl: str,
    evaluated_at: str,
    missing_reason: str | None = None,
    blocker_reason: str | None = None,
) -> LatestSnapshotResponse:
    if latest_snapshot_metadata is None:
        next_step_nl = (
            "Controleer storageconfiguratie of wacht op eerste opgeslagen snapshotmetadata."
        )
    else:
        next_step_nl = "Gebruik alleen metadata voor audit/status; dit is geen runtime-marktprijs."

    return LatestSnapshotResponse(
        ibkr_conid=ibkr_conid,
        status=status,
        status_nl=status_nl,
        latest_snapshot_metadata=latest_snapshot_metadata,
        evaluated_at=evaluated_at,
        missing_reason=missing_reason,
        blocker_reason=blocker_reason,
        next_step_nl=next_step_nl,
        help_nl=READINESS_HELP_NL,
        analysis_ready=False,
        suggestions_allowed=False,
        action_drafts_allowed=False,
    )


def build_asset_listing_gate(
    *,
    status: ReadinessAssetListingGateStatus,
    ibkr_conid: str | None,
    listing_id: str | None = None,
    asset_id: str | None = None,
    validation_status: str | None = None,
    safe_to_use_for_market_data: bool = False,
    blocks_market_data: bool = True,
) -> ReadinessAssetListingGate:
    status_map = {
        ReadinessAssetListingGateStatus.STORAGE_UNAVAILABLE: (
            "AssetListing-gate niet controleerbaar: storage niet beschikbaar",
            "Configureer storage om AssetListing-validatie te controleren.",
        ),
        ReadinessAssetListingGateStatus.MISSING_IBKR_CONID: (
            "IBKR conid ontbreekt",
            "Koppel eerst een gevalideerd IBKR-contract aan dit volglijst-item.",
        ),
        ReadinessAssetListingGateStatus.MISSING_LISTING: (
            "AssetListing ontbreekt",
            "Maak of koppel eerst een AssetListing-identiteit "
            "voordat toekomstige market-data runtime kan worden vrijgegeven.",
        ),
        ReadinessAssetListingGateStatus.UNVALIDATED_LISTING: (
            "AssetListing is nog niet veilig gevalideerd",
            "Werk de AssetListing-validatie bij tot de listing veilig is voor market data.",
        ),
        ReadinessAssetListingGateStatus.VALIDATED_LISTING: (
            "AssetListing is gevalideerd, maar dit is nog geen runtime market-data fetch",
            "Read-only status: wacht op een latere, expliciet geactiveerde "
            "market-data runtime-stap.",
        ),
    }
    status_nl, next_step_nl = status_map[status]
    return ReadinessAssetListingGate(
        status=status,
        listing_id=listing_id,
        asset_id=asset_id,
        ibkr_conid=ibkr_conid,
        validation_status=validation_status,
        safe_to_use_for_market_data=safe_to_use_for_market_data,
        blocks_market_data=blocks_market_data,
        status_nl=status_nl,
        next_step_nl=next_step_nl,
        audit_help_nl=(
            "Read-only status: geen market-data runtime, geen analyse, geen suggesties, "
            "geen Decision Packages, geen actiedrafts en geen orders."
        ),
    )
