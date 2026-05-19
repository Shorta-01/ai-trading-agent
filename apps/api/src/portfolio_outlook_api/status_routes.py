"""Routes for read-only status/settings summaries."""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.online_storage_status import (
    OnlineStorageStatusResponse,
    build_online_storage_status,
)
from portfolio_outlook_api.paper_setup import (
    SetupPreviewInput,
    create_setup_preview,
    get_setup_defaults,
    get_setup_status,
)
from portfolio_outlook_api.paper_setup_persistence import persist_first_run_paper_setup
from portfolio_outlook_api.status_builders import (
    build_ai_usage_summary,
    build_dutch_labels_summary,
    build_integrations_summary,
    build_settings_summary,
    build_system_status_summary,
)
from portfolio_outlook_api.status_models import (
    AiUsageSummary,
    DutchLabelsSummary,
    IntegrationsSummary,
    SettingsSummary,
    SystemStatusSummary,
)
from portfolio_outlook_api.storage_status import StorageStatusResponse, build_storage_status
from portfolio_outlook_api.system_event_mutations import (
    SystemEventMutationInput,
    mark_system_event_archived,
    mark_system_event_resolved,
)
from portfolio_outlook_api.system_event_reader import (
    ActiveSystemEventsResponse,
    list_active_system_events,
)

router = APIRouter()


@router.get("/system/status", response_model=SystemStatusSummary)
def read_system_status() -> SystemStatusSummary:
    return build_system_status_summary()


@router.get("/settings/summary", response_model=SettingsSummary)
def read_settings_summary() -> SettingsSummary:
    return build_settings_summary()


@router.get("/usage/ai/summary", response_model=AiUsageSummary)
def read_ai_usage_summary() -> AiUsageSummary:
    return build_ai_usage_summary()


@router.get("/integrations/summary", response_model=IntegrationsSummary)
def read_integrations_summary() -> IntegrationsSummary:
    return build_integrations_summary()


@router.get("/ui/dutch-labels", response_model=DutchLabelsSummary)
def read_dutch_labels() -> DutchLabelsSummary:
    return build_dutch_labels_summary()


@router.get("/portfolio/setup/status")
def read_portfolio_setup_status() -> dict[str, object]:
    return get_setup_status()


@router.get("/portfolio/setup/defaults")
def read_portfolio_setup_defaults() -> dict[str, object]:
    return get_setup_defaults()


@router.post("/portfolio/setup/preview")
def preview_portfolio_setup(payload: SetupPreviewInput) -> dict[str, object]:
    try:
        create_setup_preview(payload)
        result = persist_first_run_paper_setup(payload, settings.storage)
        if result.blocked:
            raise HTTPException(status_code=409, detail=result.response["message_nl"])
        return result.response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/storage/status", response_model=StorageStatusResponse)
def read_storage_status() -> StorageStatusResponse:
    return build_storage_status()


@router.get("/storage/status/online", response_model=OnlineStorageStatusResponse)
def read_storage_status_online() -> OnlineStorageStatusResponse:
    return build_online_storage_status(settings.storage)


@router.get("/system/events/active", response_model=ActiveSystemEventsResponse)
def read_active_system_events() -> ActiveSystemEventsResponse:
    return list_active_system_events(settings.storage)


@router.post("/system/events/{system_event_id}/resolve")
def resolve_system_event(
    system_event_id: str,
    payload: Annotated[SystemEventMutationInput | None, Body()] = None,
) -> dict[str, object]:
    mutation_payload = payload or SystemEventMutationInput()
    result = mark_system_event_resolved(system_event_id, settings.storage, mutation_payload)
    if result.not_found:
        raise HTTPException(status_code=404, detail=result.response["message_nl"])
    if result.blocked:
        raise HTTPException(status_code=409, detail=result.response["message_nl"])
    return result.response


@router.post("/system/events/{system_event_id}/archive")
def archive_system_event(
    system_event_id: str,
    payload: Annotated[SystemEventMutationInput | None, Body()] = None,
) -> dict[str, object]:
    mutation_payload = payload or SystemEventMutationInput()
    result = mark_system_event_archived(system_event_id, settings.storage, mutation_payload)
    if result.not_found:
        raise HTTPException(status_code=404, detail=result.response["message_nl"])
    if result.blocked:
        raise HTTPException(status_code=409, detail=result.response["message_nl"])
    return result.response
