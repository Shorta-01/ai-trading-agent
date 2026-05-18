from datetime import UTC, datetime

import pytest

from portfolio_outlook_domain import (
    AIResearchRole,
    DataQualityStatus,
    PromptInjectionRisk,
    ResearchFinding,
    ResearchReport,
    ResearchReportStatus,
    ResearchRun,
    ResearchUse,
)


def test_research_models() -> None:
    ResearchRun(
        research_run_id="rr1",
        research_use=ResearchUse.ASSET_DEEP_RESEARCH,
        status=ResearchReportStatus.DRAFT,
        started_at=datetime.now(UTC),
        source_reference_ids=["s1"],
        data_quality_status=DataQualityStatus.OK,
    )

    with pytest.raises(ValueError):
        ResearchRun(
            research_run_id="rr2",
            research_use=ResearchUse.ASSET_DEEP_RESEARCH,
            status=ResearchReportStatus.COMPLETED,
            started_at=datetime.now(UTC),
            source_reference_ids=[],
            data_quality_status=DataQualityStatus.OK,
        )

    report = ResearchReport(
        research_report_id="rp1",
        research_run_id="rr1",
        status=ResearchReportStatus.DRAFT,
        ai_role=AIResearchRole.EXPLANATION,
        summary_nl="samenvatting",
        source_reference_ids=["s1"],
        created_at=datetime.now(UTC),
        data_quality_status=DataQualityStatus.OK,
        prompt_injection_risk=PromptInjectionRisk.LOW,
    )
    assert report.model_dump()["research_report_id"] == "rp1"


    with pytest.raises(ValueError):
        ResearchFinding(research_report_id="rp1", label_nl=" ", detail_nl="x")

    ResearchFinding(research_report_id="rp1", label_nl="label", detail_nl="detail").model_dump()
