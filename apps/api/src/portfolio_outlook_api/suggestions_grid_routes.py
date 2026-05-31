"""V1 suggestions-grid endpoint.

Surfaces the daily TODO grid the operator opens at 7am to see what the
system recommends today. Grouped by action label (Verkopen first,
Vermijden / Geblokkeerd last), each row annotated with NIEUW /
Gewijzigd badges computed from yesterday's persisted suggestion.

The endpoint never returns expired suggestions — only the most recent
``ready`` / ``control_needed`` / ``blocked`` row per asset is shown.
Yesterday's rows are loaded from storage purely to compute the diff
badge; they never appear in the response items.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from ai_trading_agent_storage import (
    AssetSuggestionRecord,
    SqlAlchemyAssetSuggestionRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# Locked rendering order for the grid. Verkopen first (most urgent),
# Vermijden / Geblokkeerd last (least actionable). The order is hard-coded
# rather than operator-tunable because it reflects safety ordering, not
# preference.
_GRID_SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("Verkopen", "Verkopen — directe actie"),
    ("Verminderen", "Verminderen — positie afbouwen"),
    ("Kopen", "Kopen — nieuwe positie"),
    ("Langzaam bijkopen", "Langzaam bijkopen — bestaande positie uitbreiden"),
    ("Houden", "Houden — geen actie nodig"),
    ("Bekijken", "Bekijken — eerst evidence reviewen"),
    ("Cash houden", "Cash houden — geen koopkansen"),
    ("Geen actie", "Geen actie — signaal te zwak"),
    ("Vermijden", "Vermijden — niet aankopen"),
    ("Geblokkeerd", "Geblokkeerd — voorspelling onbeschikbaar"),
)


# Diff status assigned to each grid row, computed by comparing the
# current suggestion against the most-recent prior suggestion for the
# same asset (within the 48h history window).
_DIFF_NEW = "nieuw"  # First time this asset appears in the grid
_DIFF_CHANGED = "gewijzigd"  # Same asset but different action_label
_DIFF_UNCHANGED = "ongewijzigd"  # Same asset + same action_label


class SuggestionsGridSectionItem(BaseModel):
    """One row in the grid. Mirrors the existing ``serialize_suggestion_for_response``
    payload with three extra display fields: ``diff_status`` for the
    NIEUW / Gewijzigd badge, ``previous_action_label_nl`` (the label the
    asset had yesterday, if any), and ``valid_until_age_minutes`` so the
    UI can show how stale the row is."""

    suggestion_id: str
    ibkr_conid: str
    symbol: str
    currency: str
    forecast_id: str | None
    generated_at: str
    valid_until: str
    valid_until_age_minutes: int
    risk_profile: str
    has_position: bool
    action_label: str
    action_label_nl: str
    confidence_label: str
    confidence_label_nl: str
    confidence_score: str
    rationale_nl: str
    drivers: list[str]
    blockers: list[str]
    status: str
    blocking_reason: str | None
    branch_reason_nl: str | None
    downgrade_reason_nl: str | None
    top_driver_nl: str | None
    blocking_reason_nl: str | None
    expected_return_pct: str | None
    prob_gain_pct: str | None
    diff_status: str
    previous_action_label_nl: str | None


class SuggestionsGridSection(BaseModel):
    action_label_nl: str
    section_title_nl: str
    item_count: int
    items: list[SuggestionsGridSectionItem]


class SuggestionsGridResponse(BaseModel):
    status: str
    status_nl: str
    help_nl: str
    risk_profile: str
    actions_allowed: bool
    safe_for_orders: bool
    generated_at: str | None
    section_count: int
    total_item_count: int
    new_count: int
    changed_count: int
    sections: list[SuggestionsGridSection]


_GRID_HELP_NL = (
    "Wat het systeem vandaag voorstelt te doen, gegroepeerd op actie-"
    "type en gesorteerd van urgentie naar evidence-review. Klik op "
    "een suggestie voor de volledige Decision Package. Suggesties "
    "vervallen automatisch (TTL); morgen om 07:00 wordt een verse "
    "grid berekend op basis van de end-of-day koersen."
)


def _empty_grid_response(
    *, status: str, status_nl: str
) -> SuggestionsGridResponse:
    return SuggestionsGridResponse(
        status=status,
        status_nl=status_nl,
        help_nl=_GRID_HELP_NL,
        risk_profile=settings.suggestions_risk_profile,
        actions_allowed=False,
        safe_for_orders=False,
        generated_at=None,
        section_count=0,
        total_item_count=0,
        new_count=0,
        changed_count=0,
        sections=[],
    )


def _build_history_index(
    history: tuple[AssetSuggestionRecord, ...],
    current_ids: set[str],
) -> dict[str, AssetSuggestionRecord]:
    """Group history rows by ``ibkr_conid``, keeping the most-recent
    prior row per asset (i.e. yesterday's suggestion, not today's).

    ``current_ids`` is the set of suggestion ids that the current grid
    is going to show; the prior row must NOT be one of those (else the
    "previous" would be the current and the diff would never fire).
    """

    by_conid: dict[str, AssetSuggestionRecord] = {}
    for record in history:
        if record.suggestion_id in current_ids:
            continue
        existing = by_conid.get(record.ibkr_conid)
        if existing is None or record.generated_at > existing.generated_at:
            by_conid[record.ibkr_conid] = record
    return by_conid


def _diff_status(
    current: AssetSuggestionRecord,
    previous: AssetSuggestionRecord | None,
) -> tuple[str, str | None]:
    if previous is None:
        return _DIFF_NEW, None
    if previous.action_label != current.action_label:
        return _DIFF_CHANGED, previous.action_label_nl
    return _DIFF_UNCHANGED, previous.action_label_nl


def _valid_until_age_minutes(record: AssetSuggestionRecord, now: datetime) -> int:
    """Minutes until ``valid_until``. Negative when already expired."""

    delta_seconds = (record.valid_until - now).total_seconds()
    return int(delta_seconds // 60)


def _build_section_item(
    record: AssetSuggestionRecord,
    *,
    diff_status: str,
    previous_action_label_nl: str | None,
    now: datetime,
) -> SuggestionsGridSectionItem:
    return SuggestionsGridSectionItem(
        suggestion_id=record.suggestion_id,
        ibkr_conid=record.ibkr_conid,
        symbol=record.symbol,
        currency=record.currency,
        forecast_id=record.forecast_id,
        generated_at=record.generated_at.isoformat(),
        valid_until=record.valid_until.isoformat(),
        valid_until_age_minutes=_valid_until_age_minutes(record, now),
        risk_profile=record.risk_profile,
        has_position=record.has_position,
        action_label=record.action_label,
        action_label_nl=record.action_label_nl,
        confidence_label=record.confidence_label,
        confidence_label_nl=record.confidence_label_nl,
        confidence_score=str(record.confidence_score),
        rationale_nl=record.rationale_nl,
        drivers=list(record.drivers_json or ()),
        blockers=list(record.blockers_json or ()),
        status=record.status,
        blocking_reason=record.blocking_reason,
        branch_reason_nl=record.branch_reason_nl,
        downgrade_reason_nl=record.downgrade_reason_nl,
        top_driver_nl=record.top_driver_nl,
        blocking_reason_nl=record.blocking_reason_nl,
        expected_return_pct=(
            str(record.expected_return_pct)
            if record.expected_return_pct is not None
            else None
        ),
        prob_gain_pct=(
            str(record.prob_gain_pct)
            if record.prob_gain_pct is not None
            else None
        ),
        diff_status=diff_status,
        previous_action_label_nl=previous_action_label_nl,
    )


def _group_by_section(
    items: list[tuple[AssetSuggestionRecord, str, str | None]],
    now: datetime,
) -> list[SuggestionsGridSection]:
    """Group `(record, diff_status, previous_label_nl)` triples into the
    locked section order. Sections with zero items are omitted from the
    response so the operator doesn't scroll past empty buckets."""

    bucket: dict[str, list[SuggestionsGridSectionItem]] = {}
    for record, diff_status, previous_label_nl in items:
        section_item = _build_section_item(
            record,
            diff_status=diff_status,
            previous_action_label_nl=previous_label_nl,
            now=now,
        )
        bucket.setdefault(record.action_label, []).append(section_item)

    # Sort within each section: NIEUW first, then by confidence desc,
    # then by symbol ascending so the most attention-worthy rows lead.
    def _sort_key(item: SuggestionsGridSectionItem) -> tuple[int, float, str]:
        diff_rank = (
            0
            if item.diff_status == _DIFF_NEW
            else 1
            if item.diff_status == _DIFF_CHANGED
            else 2
        )
        try:
            confidence_negative = -float(item.confidence_score)
        except (TypeError, ValueError):
            confidence_negative = 0.0
        return (diff_rank, confidence_negative, item.symbol)

    sections: list[SuggestionsGridSection] = []
    for action_label, title in _GRID_SECTION_ORDER:
        rows = bucket.get(action_label, [])
        if not rows:
            continue
        rows.sort(key=_sort_key)
        sections.append(
            SuggestionsGridSection(
                action_label_nl=action_label,
                section_title_nl=title,
                item_count=len(rows),
                items=rows,
            )
        )
    return sections


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise StorageConnectionError("storage_disabled")
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


@router.get("/suggestions/grid", response_model=SuggestionsGridResponse)
def get_suggestions_grid() -> SuggestionsGridResponse:
    """Return the daily TODO grid the operator opens at 7am.

    Sections are returned in locked safety order: Verkopen first,
    Geblokkeerd last. Each row carries a ``diff_status`` (nieuw /
    gewijzigd / ongewijzigd) computed by comparing against the most
    recent prior suggestion for the same asset.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty_grid_response(
            status="not_configured",
            status_nl="Opslag niet geconfigureerd",
        )

    now = datetime.now(UTC)
    history_cutoff = now - timedelta(hours=48)

    try:
        provider = _storage_provider()
        with provider.checked_connection(require_writable=False) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            suggestion_repo = SqlAlchemyAssetSuggestionRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return _empty_grid_response(
                    status="no_ibkr_sync_run",
                    status_nl="Geen IBKR-sync gevonden",
                )

            # The grid covers any asset that received a suggestion in the
            # last 48h — held positions surface via the morning chain, and
            # cold-start ``Kopen`` recos surface the same way. The IBKR
            # sync existence check above is enough; we don't need to
            # restrict the history fetch by held conids.
            history_result = suggestion_repo.list_asset_suggestions_generated_since(
                history_cutoff
            )
            history_records = history_result.records

            # Most-recent record per conid is "current"; everything else
            # is treated as history for diff purposes.
            current_by_conid: dict[str, AssetSuggestionRecord] = {}
            for record in history_records:
                existing = current_by_conid.get(record.ibkr_conid)
                if existing is None or record.generated_at > existing.generated_at:
                    current_by_conid[record.ibkr_conid] = record

            if not current_by_conid:
                return _empty_grid_response(
                    status="no_suggestions",
                    status_nl="Nog geen suggesties beschikbaar",
                )

            current_ids = {r.suggestion_id for r in current_by_conid.values()}
            history_index = _build_history_index(history_records, current_ids)

            items: list[tuple[AssetSuggestionRecord, str, str | None]] = []
            for conid, current in current_by_conid.items():
                # Skip rows whose ``valid_until`` is in the past — those
                # are expired and should not appear in the grid even if
                # they're the most recent we have for the asset.
                if current.valid_until < now:
                    continue
                previous = history_index.get(conid)
                diff_status, previous_label_nl = _diff_status(current, previous)
                items.append((current, diff_status, previous_label_nl))

            if not items:
                return _empty_grid_response(
                    status="all_expired",
                    status_nl=(
                        "Alle suggesties zijn verlopen; morgen 07:00 "
                        "verschijnt een verse grid"
                    ),
                )

            sections = _group_by_section(items, now=now)
            total_items = sum(s.item_count for s in sections)
            new_count = sum(
                1
                for s in sections
                for item in s.items
                if item.diff_status == _DIFF_NEW
            )
            changed_count = sum(
                1
                for s in sections
                for item in s.items
                if item.diff_status == _DIFF_CHANGED
            )

            generated_at = max(
                (current.generated_at for current, _, _ in items)
            ).isoformat()

            return SuggestionsGridResponse(
                status="ok",
                status_nl=(
                    f"{total_items} suggesties in {len(sections)} secties"
                    + (f" ({new_count} nieuw)" if new_count else "")
                ),
                help_nl=_GRID_HELP_NL,
                risk_profile=settings.suggestions_risk_profile,
                actions_allowed=False,
                safe_for_orders=False,
                generated_at=generated_at,
                section_count=len(sections),
                total_item_count=total_items,
                new_count=new_count,
                changed_count=changed_count,
                sections=sections,
            )
    except StorageConnectionError as exc:
        logger.warning("suggestions-grid storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc


def get_grid_section_order() -> tuple[tuple[str, str], ...]:
    """Exposed for tests that need to assert the locked rendering order."""

    return _GRID_SECTION_ORDER


__all__: tuple[Any, ...] = (
    "router",
    "get_grid_section_order",
    "SuggestionsGridResponse",
    "SuggestionsGridSection",
    "SuggestionsGridSectionItem",
)
