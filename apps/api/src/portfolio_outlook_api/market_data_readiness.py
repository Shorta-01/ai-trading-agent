"""Typed read-only market-data readiness response contracts and builders."""

from datetime import UTC, datetime
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


class ReadinessRow(BaseModel):
    watchlist_item_id: str
    asset_id: str | None
    ibkr_conid: str | None
    symbol: str
    readiness_status: str
    status: str
    freshness_status: str
    blocker_code: str | None
    blocker_reason_nl: str
    required_identity_fields: list[str]
    missing_identity_fields: list[str]
    validation_status: ReadinessValidationStatus
    evaluated_at: str
    latest_snapshot_metadata: ReadinessSnapshotMetadata | None
    snapshot_metadata_present: bool
    next_step_nl: str
    audit_help_nl: str
    help_nl: str


class ReadinessListResponse(BaseModel):
    items: list[ReadinessRow]
    help_nl: str


class ReadinessDetailResponse(BaseModel):
    item: ReadinessRow | None
    message_nl: str | None = None


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_readiness_row(
    item: ReadinessWatchlistItemLike,
    snapshot_metadata: ReadinessSnapshotMetadata | None,
    *,
    evaluated_at: str,
) -> ReadinessRow:
    conid = (item.ibkr_conid or "").strip()
    conid_present = bool(conid)
    validation_ok = item.ibkr_validation_status == "valid"
    ready = validation_ok and conid_present
    freshness_status = "snapshot_available" if snapshot_metadata else "missing_snapshot"
    status = "ready" if ready else "blocked"
    blocker_code = None if ready else "missing_or_unvalidated_ibkr_contract"

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
        evaluated_at=evaluated_at,
        latest_snapshot_metadata=snapshot_metadata,
        snapshot_metadata_present=snapshot_metadata is not None,
        next_step_nl=next_step_nl,
        audit_help_nl=(
            "Dit is een read-only audit/statuscontrole. Geen market-data runtime, "
            "geen fetch, geen analyse en geen suggestievrijgave."
        ),
        help_nl="Geen market-data runtime actief; alleen readiness/foundation-status.",
    )
