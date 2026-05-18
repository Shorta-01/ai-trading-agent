from datetime import datetime, timezone
import pytest
from portfolio_outlook_domain import *


def test_sources_models():
    s=SourceReference(source_reference_id='s1', source_type=ResearchSourceType.WEBSITE, title='Title', url='https://x', retrieved_at=datetime.now(timezone.utc), data_quality_status=DataQualityStatus.OK, prompt_injection_risk=PromptInjectionRisk.LOW)
    assert s.model_dump()['title']=='Title'
    with pytest.raises(ValueError): SourceReference(source_reference_id='s1', source_type=ResearchSourceType.WEBSITE, title=' ', retrieved_at=datetime.now(timezone.utc), data_quality_status=DataQualityStatus.OK, prompt_injection_risk=PromptInjectionRisk.LOW)
    with pytest.raises(ValueError): s.model_copy(update={'url':' '})
    RawDataArchiveReference(raw_data_archive_id='r1', source_type=ResearchSourceType.OTHER, storage_path='/archive/path', content_hash='abc', received_at=datetime.now(timezone.utc), schema_version='v1', data_quality_status=DataQualityStatus.OK)
    ResearchArchiveReference(research_archive_id='ra1', research_run_id='rr1', storage_path='/research/path', content_hash='abc', created_at=datetime.now(timezone.utc), schema_version='v1')
