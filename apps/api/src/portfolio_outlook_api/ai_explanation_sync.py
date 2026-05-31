"""AI explanation orchestrator (Slice 10).

Generates one ``DecisionPackageExplanationRecord`` per
``(decision_package_id, decision_package_content_hash)`` pair. The
orchestrator:

1. Refuses to run if no provider is available (factory returned
   :class:`ExplanationProviderUnavailable`).
2. Builds a canonical input bundle from the persisted Decision Package
   + any linked research snippet.
3. Hashes the canonical input (audit anchor: the *exact* evidence the
   model saw) and asks the provider for a Dutch explanation.
4. Validates the output via :func:`validate_explanation_output` —
   blocks the result if any number is hallucinated, the disclaimer is
   missing, or the output is empty/too long.
5. Persists the explanation row and an append-only entry per evidence
   source on the ``explanation_evidence_ledger``.

Hard contract: this module never originates a financial number; it
only paraphrases what the persisted Decision Package + research evidence
already contain.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetDecisionPackageRecord,
    DecisionPackageExplanationRecord,
    ExplanationEvidenceLedgerRecord,
    ResearchSourceRecord,
)
from portfolio_outlook_portfolio import (
    EXPLANATION_STATUS_FAILED,
    EXPLANATION_STATUS_GENERATED,
    LOCKED_RISK_DISCLAIMER_NL,
    validate_explanation_output,
)

from portfolio_outlook_api.ai_explanation_provider import (
    ExplanationProviderInputs,
    ExplanationProviderProtocol,
    ExplanationProviderUnavailable,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExplanationReport:
    requested_at: datetime
    completed_at: datetime
    status: str
    status_nl: str
    help_nl: str
    explanation_id: str | None
    blocking_reason: str | None
    hallucinated_numbers: tuple[str, ...]


class _ExplanationRepoProtocol(Protocol):
    def save_decision_package_explanation(
        self, record: DecisionPackageExplanationRecord
    ) -> object: ...

    def save_explanation_evidence_ledger_entry(
        self, record: ExplanationEvidenceLedgerRecord
    ) -> object: ...


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_canonical_input(
    *,
    package: AssetDecisionPackageRecord,
    research_sources: tuple[ResearchSourceRecord, ...],
) -> str:
    """Serialise the package + linked research into the model's input.

    The serialisation is canonical JSON with sorted keys so the hash is
    deterministic across runs. The serializer mirrors the fields the
    operator can already see in the persisted package; nothing new is
    invented.
    """

    payload: dict[str, object] = {
        "decision_package_id": package.decision_package_id,
        "content_hash": package.content_hash,
        "symbol": package.symbol,
        "currency": package.currency,
        "risk_profile": package.risk_profile,
        "suggestion_action_label": package.suggestion_action_label,
        "suggestion_action_label_nl": package.suggestion_action_label_nl,
        "suggestion_confidence_label_nl": package.suggestion_confidence_label_nl,
        "suggestion_status": package.suggestion_status,
        "has_position": package.has_position,
        "market_last_price": (
            str(package.market_last_price) if package.market_last_price else None
        ),
        "market_freshness_status": package.market_freshness_status,
        "position_quantity": (
            str(package.position_quantity) if package.position_quantity else None
        ),
        "position_average_cost": (
            str(package.position_average_cost)
            if package.position_average_cost
            else None
        ),
        "cash_amount": str(package.cash_amount) if package.cash_amount else None,
        "cash_base_currency": package.cash_base_currency,
        "forecast_p10_price": (
            str(package.forecast_p10_price) if package.forecast_p10_price else None
        ),
        "forecast_p50_price": (
            str(package.forecast_p50_price) if package.forecast_p50_price else None
        ),
        "forecast_p90_price": (
            str(package.forecast_p90_price) if package.forecast_p90_price else None
        ),
        "forecast_prob_gain": (
            str(package.forecast_prob_gain) if package.forecast_prob_gain else None
        ),
        "forecast_prob_loss": (
            str(package.forecast_prob_loss) if package.forecast_prob_loss else None
        ),
        "forecast_horizon_days": package.forecast_horizon_days,
        "research_evidence_count": package.research_evidence_count,
        "research_credibility_summary": package.research_credibility_summary,
        "research_freshness_status": package.research_freshness_status,
        "research_snippet_nl": package.research_snippet_nl,
        "rationale_nl": package.rationale_nl,
        "explanation_nl": package.explanation_nl,
        "research_sources": [
            {
                "library_source_id": s.library_source_id,
                "title": s.title,
                "source_type": s.source_type,
                "source_credibility_level": s.source_credibility_level,
                "prompt_injection_risk_level": s.prompt_injection_risk_level,
            }
            for s in research_sources
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _build_evidence_ledger(
    *,
    explanation_id: str,
    package: AssetDecisionPackageRecord,
    research_sources: Iterable[ResearchSourceRecord],
    now: datetime,
) -> list[ExplanationEvidenceLedgerRecord]:
    entries: list[ExplanationEvidenceLedgerRecord] = [
        ExplanationEvidenceLedgerRecord(
            ledger_id=f"led_{uuid4().hex}",
            explanation_id=explanation_id,
            evidence_kind="decision_package",
            evidence_reference_id=package.decision_package_id,
            evidence_content_hash=package.content_hash,
            linked_at=now,
        )
    ]
    for source in research_sources:
        entries.append(
            ExplanationEvidenceLedgerRecord(
                ledger_id=f"led_{uuid4().hex}",
                explanation_id=explanation_id,
                evidence_kind="research_source",
                evidence_reference_id=source.library_source_id,
                evidence_content_hash=source.content_hash_sha256 or "missing",
                linked_at=now,
            )
        )
    return entries


def generate_explanation(
    *,
    package: AssetDecisionPackageRecord,
    research_sources: tuple[ResearchSourceRecord, ...],
    provider: ExplanationProviderProtocol | ExplanationProviderUnavailable,
    repo: _ExplanationRepoProtocol,
    max_output_chars: int,
) -> ExplanationReport:
    """Build and persist one explanation; surface any blocking reason."""

    requested_at = datetime.now(UTC)
    if isinstance(provider, ExplanationProviderUnavailable):
        return ExplanationReport(
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
            status="provider_unavailable",
            status_nl="Geen AI-uitleg beschikbaar",
            help_nl=provider.detail_nl,
            explanation_id=None,
            blocking_reason=provider.reason,
            hallucinated_numbers=(),
        )

    input_text = _build_canonical_input(
        package=package,
        research_sources=research_sources,
    )
    input_evidence_hash = _hash_text(input_text)
    provider_inputs = ExplanationProviderInputs(
        decision_package_id=package.decision_package_id,
        decision_package_content_hash=package.content_hash,
        symbol=package.symbol,
        risk_profile=package.risk_profile,
        rationale_nl=package.rationale_nl,
        package_explanation_nl=package.explanation_nl,
        research_snippet_nl=package.research_snippet_nl,
        input_text=input_text,
    )

    try:
        provider_result = provider.generate(provider_inputs)
    except Exception as exc:  # noqa: BLE001 — boundary catch, surfaced as failed
        logger.warning("explanation provider failed: %s", exc)
        return ExplanationReport(
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
            status=EXPLANATION_STATUS_FAILED,
            status_nl="AI-uitleg mislukt",
            help_nl=f"De provider gaf een fout: {exc}",
            explanation_id=None,
            blocking_reason="provider_error",
            hallucinated_numbers=(),
        )

    # The input_evidence_text fed to the validator is the canonical
    # package summary (numbers + Dutch text). The validator extracts
    # numeric tokens from this text; the canonical JSON contains every
    # number the package carries.
    validation = validate_explanation_output(
        output_text=provider_result.output_text,
        input_evidence_text=input_text,
        max_output_chars=max_output_chars,
        disclaimer=LOCKED_RISK_DISCLAIMER_NL,
    )

    now = datetime.now(UTC)
    explanation_id = f"exp_{uuid4().hex}"
    explanation = DecisionPackageExplanationRecord(
        explanation_id=explanation_id,
        decision_package_id=package.decision_package_id,
        decision_package_content_hash=package.content_hash,
        ibkr_conid=package.ibkr_conid,
        symbol=package.symbol,
        model_provider_code=provider_result.model_provider_code,
        model_name=provider_result.model_name,
        model_version=provider_result.model_version,
        input_evidence_hash=input_evidence_hash,
        output_text_hash=_hash_text(provider_result.output_text),
        explanation_nl=provider_result.output_text,
        risk_disclaimer_nl=LOCKED_RISK_DISCLAIMER_NL,
        status=validation.status,
        blocking_reason=validation.blocking_reason,
        hallucinated_numbers_json=(
            validation.hallucinated_numbers if validation.hallucinated_numbers else None
        ),
        generated_at=now,
        created_at=now,
    )

    try:
        repo.save_decision_package_explanation(explanation)
        for ledger_entry in _build_evidence_ledger(
            explanation_id=explanation_id,
            package=package,
            research_sources=research_sources,
            now=now,
        ):
            repo.save_explanation_evidence_ledger_entry(ledger_entry)
    except Exception as exc:  # noqa: BLE001
        logger.exception("explanation persistence failed")
        return ExplanationReport(
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
            status=EXPLANATION_STATUS_FAILED,
            status_nl="AI-uitleg niet opgeslagen",
            help_nl=f"De opslag gaf een fout: {exc}",
            explanation_id=None,
            blocking_reason="persistence_error",
            hallucinated_numbers=(),
        )

    if validation.status == EXPLANATION_STATUS_GENERATED:
        status_nl = "AI-uitleg gegenereerd"
        help_nl = (
            "Samenvatting van bewijs; geen advies. AI bedacht geen nieuwe "
            "getallen."
        )
    else:
        status_nl = "AI-uitleg geblokkeerd"
        help_nl = (
            "De AI-output overtrad de safety-regels en is opgeslagen als "
            "geblokkeerd. Zie blocking_reason voor details."
        )

    return ExplanationReport(
        requested_at=requested_at,
        completed_at=datetime.now(UTC),
        status=validation.status,
        status_nl=status_nl,
        help_nl=help_nl,
        explanation_id=explanation_id,
        blocking_reason=validation.blocking_reason,
        hallucinated_numbers=validation.hallucinated_numbers,
    )


def serialize_explanation_for_response(
    record: DecisionPackageExplanationRecord,
) -> dict[str, object]:
    return {
        "explanation_id": record.explanation_id,
        "decision_package_id": record.decision_package_id,
        "decision_package_content_hash": record.decision_package_content_hash,
        "ibkr_conid": record.ibkr_conid,
        "symbol": record.symbol,
        "model_provider_code": record.model_provider_code,
        "model_name": record.model_name,
        "model_version": record.model_version,
        "input_evidence_hash": record.input_evidence_hash,
        "output_text_hash": record.output_text_hash,
        "explanation_nl": record.explanation_nl,
        "risk_disclaimer_nl": record.risk_disclaimer_nl,
        "status": record.status,
        "blocking_reason": record.blocking_reason,
        "hallucinated_numbers": list(record.hallucinated_numbers_json or ()),
        "generated_at": record.generated_at.isoformat(),
        "safe_for_self_learning": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@dataclass(frozen=True)
class MorningBatchReport:
    """Aggregate result of the per-Decision-Package explanation batch.

    Returned by :func:`generate_explanations_for_morning_batch`. The
    counts let the operator audit how many explanations Claude
    generated overnight without scrolling per-package responses.
    """

    requested_at: datetime
    completed_at: datetime
    package_count: int
    generated_count: int
    blocked_count: int
    skipped_count: int
    blocking_reasons: tuple[str, ...]


def generate_explanations_for_morning_batch(
    *,
    decision_packages: Sequence[AssetDecisionPackageRecord],
    research_sources_for_symbol: Callable[
        [str], tuple[ResearchSourceRecord, ...]
    ],
    provider: ExplanationProviderProtocol | ExplanationProviderUnavailable,
    repo: _ExplanationRepoProtocol,
    max_output_chars: int,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> MorningBatchReport:
    """Pre-compute one Claude explanation per Decision Package.

    Iterates ``decision_packages`` in order; for each, fetches research
    sources via the callback + calls :func:`generate_explanation`. Per-
    package errors don't abort the batch — they're folded into the
    ``blocked_count`` + ``blocking_reasons`` counters.

    The provider-unavailable case (budget exceeded, real-client off,
    etc.) short-circuits: every package is reported as ``skipped`` so
    the operator sees a single deterministic reason in the audit row
    rather than N copies.
    """

    requested_at = now_provider()

    # Short-circuit: a single provider-unavailable bubble lets the
    # caller see ONE reason instead of N copies. We still report the
    # package count so the audit row reflects what would have been
    # attempted.
    if isinstance(provider, ExplanationProviderUnavailable):
        return MorningBatchReport(
            requested_at=requested_at,
            completed_at=now_provider(),
            package_count=len(decision_packages),
            generated_count=0,
            blocked_count=0,
            skipped_count=len(decision_packages),
            blocking_reasons=(provider.reason,),
        )

    generated = 0
    blocked = 0
    reasons: list[str] = []
    for package in decision_packages:
        sources = research_sources_for_symbol(package.symbol)
        report = generate_explanation(
            package=package,
            research_sources=sources,
            provider=provider,
            repo=repo,
            max_output_chars=max_output_chars,
        )
        if report.status == "generated":
            generated += 1
            continue
        blocked += 1
        if report.blocking_reason:
            reasons.append(report.blocking_reason)

    # De-duplicate reasons but preserve insertion order — easier to
    # eyeball in the audit row than a sorted set.
    seen: set[str] = set()
    deduped_reasons: list[str] = []
    for reason in reasons:
        if reason in seen:
            continue
        seen.add(reason)
        deduped_reasons.append(reason)

    return MorningBatchReport(
        requested_at=requested_at,
        completed_at=now_provider(),
        package_count=len(decision_packages),
        generated_count=generated,
        blocked_count=blocked,
        skipped_count=0,
        blocking_reasons=tuple(deduped_reasons),
    )


__all__ = [
    "ExplanationReport",
    "MorningBatchReport",
    "generate_explanation",
    "generate_explanations_for_morning_batch",
    "serialize_explanation_for_response",
]
