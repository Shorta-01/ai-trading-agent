from datetime import UTC, datetime

import pytest

from portfolio_outlook_domain import (
    DataQualityStatus,
    PromptInjectionRisk,
    RawDataArchiveReference,
    ResearchArchiveReference,
    ResearchSourceType,
    SourceReference,
)


def test_sources_models() -> None:
    source = SourceReference(
        source_reference_id="s1",
        source_type=ResearchSourceType.WEBSITE,
        title="Title",
        url="https://x",
        retrieved_at=datetime.now(UTC),
        data_quality_status=DataQualityStatus.OK,
        prompt_injection_risk=PromptInjectionRisk.LOW,
    )
    assert source.model_dump()["title"] == "Title"

    with pytest.raises(ValueError):
        SourceReference(
            source_reference_id="s1",
            source_type=ResearchSourceType.WEBSITE,
            title=" ",
            retrieved_at=datetime.now(UTC),
            data_quality_status=DataQualityStatus.OK,
            prompt_injection_risk=PromptInjectionRisk.LOW,
        )


    RawDataArchiveReference(
        raw_data_archive_id="r1",
        source_type=ResearchSourceType.OTHER,
        storage_path="/archive/path",
        content_hash="abc",
        received_at=datetime.now(UTC),
        schema_version="v1",
        data_quality_status=DataQualityStatus.OK,
    )

    ResearchArchiveReference(
        research_archive_id="ra1",
        research_run_id="rr1",
        storage_path="/research/path",
        content_hash="abc",
        created_at=datetime.now(UTC),
        schema_version="v1",
    )
