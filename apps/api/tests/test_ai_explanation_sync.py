"""Tests for the AI explanation orchestrator (Slice 10)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetDecisionPackageRecord,
    DecisionPackageExplanationRecord,
    ExplanationEvidenceLedgerRecord,
    ResearchSourceRecord,
)
from portfolio_outlook_portfolio import (
    BLOCKING_REASON_DISCLAIMER_MISSING,
    BLOCKING_REASON_HALLUCINATED_NUMBERS,
    EXPLANATION_STATUS_BLOCKED,
    EXPLANATION_STATUS_FAILED,
    EXPLANATION_STATUS_GENERATED,
    LOCKED_RISK_DISCLAIMER_NL,
)

from portfolio_outlook_api.ai_explanation_provider import (
    ExplanationProviderInputs,
    ExplanationProviderResult,
    ExplanationProviderUnavailable,
    StubExplanationProvider,
)
from portfolio_outlook_api.ai_explanation_sync import (
    generate_explanation,
    serialize_explanation_for_response,
)

_NOW = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)


def _package(
    *,
    decision_package_id: str = "dp-1",
    content_hash: str = "hash-aapl-1",
    symbol: str = "AAPL",
    research_snippet: str | None = "2 onderzoeksbron(nen) gekoppeld; hoge credibility.",
) -> AssetDecisionPackageRecord:
    return AssetDecisionPackageRecord(
        decision_package_id=decision_package_id,
        content_hash=content_hash,
        ibkr_conid="265598",
        symbol=symbol,
        currency="USD",
        risk_profile="Gebalanceerd",
        generated_at=_NOW,
        valid_until=_NOW,
        position_snapshot_id=None,
        position_quantity=Decimal("10"),
        position_average_cost=Decimal("150"),
        cash_snapshot_id=None,
        cash_base_currency="USD",
        cash_amount=Decimal("5000"),
        market_snapshot_id=None,
        market_last_price=Decimal("180"),
        market_freshness_status="fresh",
        market_provider_code="eodhd",
        market_provider_as_of=_NOW,
        fx_pair=None,
        fx_rate=None,
        fx_freshness_status=None,
        forecast_id="fc-1",
        forecast_model_code="baseline_gbm",
        forecast_model_version="v1",
        forecast_horizon_days=21,
        forecast_p10_price=Decimal("170"),
        forecast_p50_price=Decimal("182"),
        forecast_p90_price=Decimal("194"),
        forecast_prob_gain=Decimal("0.62"),
        forecast_prob_loss=Decimal("0.38"),
        forecast_expected_return_pct=Decimal("1.5"),
        forecast_expected_volatility_annual=Decimal("0.22"),
        forecast_downside_risk_score=Decimal("6.0"),
        forecast_confidence_score=Decimal("0.85"),
        suggestion_id="sug-1",
        suggestion_model_code="baseline_label_translator",
        suggestion_action_label="Houden",
        suggestion_action_label_nl="Houden",
        suggestion_confidence_label="Hoog",
        suggestion_confidence_label_nl="Hoog",
        suggestion_status="ready",
        has_position=True,
        gate_outcomes_json=None,
        evidence_links_json=None,
        audit_links_json=None,
        rationale_nl="Houden vanwege lichte stijging in baseline-voorspelling.",
        explanation_nl="Decision Package voor AAPL: action label Houden bij hoog vertrouwen.",
        status="ready",
        blocking_reason=None,
        research_evidence_count=2,
        research_credibility_summary="high",
        research_freshness_status="fresh",
        research_blocking_reason=None,
        research_snippet_nl=research_snippet,
    )


def _research_source() -> ResearchSourceRecord:
    return ResearchSourceRecord(
        library_source_id="src-1",
        source_kind="uploaded_file",
        status="active",
        classification_status="completed",
        extraction_status="completed",
        analysis_status="completed",
        asset_symbol="AAPL",
        asset_name="Apple Inc.",
        title="Q1 2025 Earnings",
        document_type="earnings",
        source_type="filing",
        source_credibility_level="high",
        prompt_injection_risk_level="low",
        content_hash_sha256="research-hash-1",
        archive_storage_uri="file://x",
        raw_source_available=True,
        created_at=_NOW,
        updated_at=_NOW,
        archived_at=None,
        schema_version="1",
        explanation_nl="ok",
    )


class FakeExplanationRepo:
    def __init__(self, *, persistence_fails: bool = False) -> None:
        self.saved_explanations: list[DecisionPackageExplanationRecord] = []
        self.saved_ledger: list[ExplanationEvidenceLedgerRecord] = []
        self._fail = persistence_fails

    def save_decision_package_explanation(
        self, record: DecisionPackageExplanationRecord
    ) -> object:
        if self._fail:
            raise RuntimeError("storage-fail")
        self.saved_explanations.append(record)
        return None

    def save_explanation_evidence_ledger_entry(
        self, record: ExplanationEvidenceLedgerRecord
    ) -> object:
        self.saved_ledger.append(record)
        return None


def test_stub_provider_happy_path_persists_generated_explanation() -> None:
    repo = FakeExplanationRepo()
    package = _package()
    sources = (_research_source(),)

    report = generate_explanation(
        package=package,
        research_sources=sources,
        provider=StubExplanationProvider(),
        repo=repo,
        max_output_chars=2000,
    )

    assert report.status == EXPLANATION_STATUS_GENERATED
    assert report.explanation_id is not None
    assert report.blocking_reason is None
    assert report.hallucinated_numbers == ()
    assert len(repo.saved_explanations) == 1
    persisted = repo.saved_explanations[0]
    assert persisted.decision_package_id == "dp-1"
    assert persisted.decision_package_content_hash == "hash-aapl-1"
    assert persisted.symbol == "AAPL"
    assert persisted.risk_disclaimer_nl == LOCKED_RISK_DISCLAIMER_NL
    assert LOCKED_RISK_DISCLAIMER_NL in persisted.explanation_nl
    assert persisted.safe_for_self_learning is False
    assert persisted.safe_for_action_drafts is False
    assert persisted.safe_for_orders is False
    # Ledger has at least one entry for the package + one per source.
    assert len(repo.saved_ledger) == 2
    assert {e.evidence_kind for e in repo.saved_ledger} == {
        "decision_package",
        "research_source",
    }


def test_provider_unavailable_yields_no_persistence() -> None:
    repo = FakeExplanationRepo()
    report = generate_explanation(
        package=_package(),
        research_sources=(),
        provider=ExplanationProviderUnavailable(
            reason="ai_explanation_disabled",
            detail_nl="AI uitleg uitgeschakeld.",
        ),
        repo=repo,
        max_output_chars=2000,
    )
    assert report.status == "provider_unavailable"
    assert report.explanation_id is None
    assert report.blocking_reason == "ai_explanation_disabled"
    assert len(repo.saved_explanations) == 0
    assert len(repo.saved_ledger) == 0


def test_hallucinated_number_in_provider_output_is_persisted_blocked() -> None:
    class _HallucinatingProvider:
        def generate(
            self, inputs: ExplanationProviderInputs
        ) -> ExplanationProviderResult:
            return ExplanationProviderResult(
                output_text=(
                    f"Doelprijs is 999. {LOCKED_RISK_DISCLAIMER_NL}"
                ),
                model_provider_code="evil",
                model_name="hallucinator",
                model_version="v1",
            )

    repo = FakeExplanationRepo()
    report = generate_explanation(
        package=_package(),
        research_sources=(),
        provider=_HallucinatingProvider(),
        repo=repo,
        max_output_chars=2000,
    )
    assert report.status == EXPLANATION_STATUS_BLOCKED
    assert report.blocking_reason == BLOCKING_REASON_HALLUCINATED_NUMBERS
    assert "999" in report.hallucinated_numbers
    # Record is still persisted, but with status=blocked so the UI knows.
    assert len(repo.saved_explanations) == 1
    assert repo.saved_explanations[0].status == EXPLANATION_STATUS_BLOCKED
    assert repo.saved_explanations[0].hallucinated_numbers_json == ("999",)


def test_missing_disclaimer_blocks_persistence_as_blocked() -> None:
    class _NoDisclaimerProvider:
        def generate(
            self, inputs: ExplanationProviderInputs
        ) -> ExplanationProviderResult:
            return ExplanationProviderResult(
                output_text="AAPL noteert 180. Geen disclaimer.",
                model_provider_code="stub",
                model_name="x",
                model_version="v1",
            )

    repo = FakeExplanationRepo()
    report = generate_explanation(
        package=_package(),
        research_sources=(),
        provider=_NoDisclaimerProvider(),
        repo=repo,
        max_output_chars=2000,
    )
    assert report.status == EXPLANATION_STATUS_BLOCKED
    assert report.blocking_reason == BLOCKING_REASON_DISCLAIMER_MISSING


def test_provider_exception_is_classified_as_failed_without_persistence() -> None:
    class _RaisingProvider:
        def generate(
            self, inputs: ExplanationProviderInputs
        ) -> ExplanationProviderResult:
            raise RuntimeError("model timeout")

    repo = FakeExplanationRepo()
    report = generate_explanation(
        package=_package(),
        research_sources=(),
        provider=_RaisingProvider(),
        repo=repo,
        max_output_chars=2000,
    )
    assert report.status == EXPLANATION_STATUS_FAILED
    assert report.blocking_reason == "provider_error"
    assert len(repo.saved_explanations) == 0


def test_persistence_failure_is_classified_as_failed() -> None:
    repo = FakeExplanationRepo(persistence_fails=True)
    report = generate_explanation(
        package=_package(),
        research_sources=(),
        provider=StubExplanationProvider(),
        repo=repo,
        max_output_chars=2000,
    )
    assert report.status == EXPLANATION_STATUS_FAILED
    assert report.blocking_reason == "persistence_error"


def test_input_evidence_hash_changes_when_research_changes() -> None:
    repo_a = FakeExplanationRepo()
    repo_b = FakeExplanationRepo()
    pkg = _package()
    src = _research_source()

    generate_explanation(
        package=pkg,
        research_sources=(),
        provider=StubExplanationProvider(),
        repo=repo_a,
        max_output_chars=2000,
    )
    generate_explanation(
        package=pkg,
        research_sources=(src,),
        provider=StubExplanationProvider(),
        repo=repo_b,
        max_output_chars=2000,
    )
    assert repo_a.saved_explanations[0].input_evidence_hash != (
        repo_b.saved_explanations[0].input_evidence_hash
    )


def test_serializer_strips_internals_and_emits_safety_flags_false() -> None:
    repo = FakeExplanationRepo()
    generate_explanation(
        package=_package(),
        research_sources=(),
        provider=StubExplanationProvider(),
        repo=repo,
        max_output_chars=2000,
    )
    payload = serialize_explanation_for_response(repo.saved_explanations[0])
    assert payload["status"] == EXPLANATION_STATUS_GENERATED
    assert payload["safe_for_self_learning"] is False
    assert payload["safe_for_action_drafts"] is False
    assert payload["safe_for_orders"] is False
    assert payload["risk_disclaimer_nl"] == LOCKED_RISK_DISCLAIMER_NL
    assert payload["hallucinated_numbers"] == []
