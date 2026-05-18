from datetime import datetime, timezone
import pytest
from portfolio_outlook_domain import *


def test_research_models():
    ResearchRun(research_run_id='rr1', research_use=ResearchUse.ASSET_DEEP_RESEARCH, status=ResearchReportStatus.DRAFT, started_at=datetime.now(timezone.utc), source_reference_ids=['s1'], data_quality_status=DataQualityStatus.OK)
    with pytest.raises(ValueError): ResearchRun(research_run_id='rr2', research_use=ResearchUse.ASSET_DEEP_RESEARCH, status=ResearchReportStatus.COMPLETED, started_at=datetime.now(timezone.utc), source_reference_ids=[], data_quality_status=DataQualityStatus.OK)
    rep=ResearchReport(research_report_id='rp1', research_run_id='rr1', status=ResearchReportStatus.DRAFT, ai_role=AIResearchRole.EXPLANATION, summary_nl='samenvatting', source_reference_ids=['s1'], created_at=datetime.now(timezone.utc), data_quality_status=DataQualityStatus.OK, prompt_injection_risk=PromptInjectionRisk.LOW)
    assert rep.model_dump()['research_report_id']=='rp1'
    with pytest.raises(ValueError): rep.model_copy(update={'summary_nl':' '})
    with pytest.raises(ValueError): rep.model_copy(update={'prompt_injection_risk':PromptInjectionRisk.BLOCKED, 'status':ResearchReportStatus.DRAFT})
    with pytest.raises(ValueError): rep.model_copy(update={'data_quality_status':DataQualityStatus.FAILED, 'status':ResearchReportStatus.COMPLETED})
    with pytest.raises(ValueError): ResearchFinding(research_report_id='rp1', label_nl=' ', detail_nl='x')
    ResearchFinding(research_report_id='rp1', label_nl='label', detail_nl='detail').model_dump()
