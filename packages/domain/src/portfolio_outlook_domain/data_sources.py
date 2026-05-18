from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .enums import (
    DataAccessMethod,
    DataCostTier,
    DataDomain,
    DataFailurePolicy,
    DataFreshnessClass,
    DataProviderKind,
    DataUsageStatus,
    DataUsePermission,
    SourceReliabilityTier,
)
from .identifiers import (
    DataSourceId,
    DataSourcePolicyId,
    DataSourceRegistryId,
    DataSourceRequirementId,
    RawDataArchiveId,
    ResearchArchiveId,
)
from .primitives import DomainBaseModel


class DataSourcePolicy(DomainBaseModel):
    data_source_policy_id: DataSourcePolicyId
    usage_status: DataUsageStatus
    reliability_tier: SourceReliabilityTier
    allowed_uses: list[DataUsePermission] = Field(default_factory=list)
    requires_manual_review: bool = False
    requires_license_review: bool = False
    legal_review_status_nl: str
    notes_nl: str

    @model_validator(mode="after")
    def validate_policy(self) -> "DataSourcePolicy":
        if self.usage_status is DataUsageStatus.BLOCKED and self.allowed_uses:
            raise ValueError("blocked policy mag geen allowed_uses hebben")
        if self.usage_status is DataUsageStatus.REVIEW_REQUIRED and not (
            self.requires_manual_review or self.requires_license_review
        ):
            raise ValueError("review_required policy vereist manual of license review")
        if DataUsePermission.SUGGESTION_ELIGIBILITY in self.allowed_uses:
            if self.usage_status not in {
                DataUsageStatus.ALLOWED,
                DataUsageStatus.ALLOWED_WITH_LIMITS,
            }:
                raise ValueError("suggestion eligibility vereist allowed status")
            if self.reliability_tier in {
                SourceReliabilityTier.UNKNOWN,
                SourceReliabilityTier.UNVERIFIED,
            }:
                raise ValueError("suggestion eligibility vereist gekende betrouwbaarheid")
        if not self.notes_nl.strip() or not self.legal_review_status_nl.strip():
            raise ValueError("notes_nl en legal_review_status_nl zijn verplicht")
        return self


class DataSourceRequirement(DomainBaseModel):
    data_source_requirement_id: DataSourceRequirementId
    name: str
    data_domain: DataDomain
    use_permission: DataUsePermission
    freshness_class: DataFreshnessClass
    failure_policy: DataFailurePolicy
    notes_nl: str

    @model_validator(mode="after")
    def validate_requirement(self) -> "DataSourceRequirement":
        if (
            self.use_permission
            in {
                DataUsePermission.SUGGESTION_ELIGIBILITY,
                DataUsePermission.PORTFOLIO_VALUATION,
            }
            and self.failure_policy is DataFailurePolicy.IGNORE_IF_OPTIONAL
        ):
            raise ValueError("suggestie en waardering vereisen strengere failure policy")
        if not self.name.strip() or not self.notes_nl.strip():
            raise ValueError("name en notes_nl zijn verplicht")
        return self


class DataSourceDefinition(DomainBaseModel):
    data_source_id: DataSourceId
    name: str
    provider_kind: DataProviderKind
    data_domains: list[DataDomain]
    access_method: DataAccessMethod
    cost_tier: DataCostTier
    policy: DataSourcePolicy
    source_url: str | None = None
    raw_data_archive_id: RawDataArchiveId | None = None
    research_archive_id: ResearchArchiveId | None = None
    notes_nl: str

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("source_url mag niet leeg zijn")
        lowered = value.lower()
        if "apikey=" in lowered or "token=" in lowered or "secret=" in lowered:
            raise ValueError("source_url mag geen secrets bevatten")
        return value

    @model_validator(mode="after")
    def validate_source(self) -> "DataSourceDefinition":
        if not self.name.strip() or not self.notes_nl.strip():
            raise ValueError("name en notes_nl zijn verplicht")
        if not self.data_domains:
            raise ValueError("data_domains mag niet leeg zijn")
        if DataUsePermission.SUGGESTION_ELIGIBILITY in self.policy.allowed_uses and (
            self.provider_kind
            in {
                DataProviderKind.PUBLIC_NEWS,
                DataProviderKind.PUBLIC_WEBSITE,
            }
        ):
            raise ValueError("public news/websites niet voor suggestion eligibility")
        return self


class DataSourceRegistry(DomainBaseModel):
    data_source_registry_id: DataSourceRegistryId
    created_at: datetime
    sources: list[DataSourceDefinition] = Field(default_factory=list)
    requirements: list[DataSourceRequirement] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_registry(self) -> "DataSourceRegistry":
        source_ids = [source.data_source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("duplicate data_source_id in registry")
        req_ids = [req.data_source_requirement_id for req in self.requirements]
        if len(req_ids) != len(set(req_ids)):
            raise ValueError("duplicate data_source_requirement_id in registry")
        return self


def can_use_source_for(source: DataSourceDefinition, use: DataUsePermission) -> bool:
    return use in source.policy.allowed_uses


def requires_block_when_missing(requirement: DataSourceRequirement) -> bool:
    return requirement.failure_policy is DataFailurePolicy.BLOCK_OPERATION


def find_sources_for_domain(
    registry: DataSourceRegistry,
    data_domain: DataDomain,
) -> list[DataSourceDefinition]:
    return [source for source in registry.sources if data_domain in source.data_domains]


def build_default_data_source_registry(created_at: datetime) -> DataSourceRegistry:
    strict = DataSourcePolicy(
        data_source_policy_id="policy_strict_official",
        usage_status=DataUsageStatus.ALLOWED,
        reliability_tier=SourceReliabilityTier.HIGH,
        allowed_uses=[
            DataUsePermission.RESEARCH_CONTEXT,
            DataUsePermission.PORTFOLIO_VALUATION,
            DataUsePermission.SUGGESTION_ELIGIBILITY,
            DataUsePermission.AUDIT_EVIDENCE,
        ],
        legal_review_status_nl="Goedgekeurd voor intern gebruik.",
        notes_nl="Officiële bron met hoge betrouwbaarheid.",
    )
    limited = DataSourcePolicy(
        data_source_policy_id="policy_limited_public",
        usage_status=DataUsageStatus.ALLOWED_WITH_LIMITS,
        reliability_tier=SourceReliabilityTier.MEDIUM,
        allowed_uses=[DataUsePermission.RESEARCH_CONTEXT, DataUsePermission.AUDIT_EVIDENCE],
        legal_review_status_nl="Alleen gebruiken met bronvermelding.",
        notes_nl="Publieke bron met beperkingen.",
    )
    review = DataSourcePolicy(
        data_source_policy_id="policy_review_required",
        usage_status=DataUsageStatus.REVIEW_REQUIRED,
        reliability_tier=SourceReliabilityTier.UNKNOWN,
        requires_manual_review=True,
        legal_review_status_nl="Nog niet juridisch nagekeken.",
        notes_nl="Eerst manuele review voor gebruik.",
    )
    blocked = DataSourcePolicy(
        data_source_policy_id="policy_blocked",
        usage_status=DataUsageStatus.BLOCKED,
        reliability_tier=SourceReliabilityTier.UNKNOWN,
        legal_review_status_nl="Niet toegestaan.",
        notes_nl="Geblokkeerd tot nader beleid.",
    )

    sources = [
        DataSourceDefinition(
            data_source_id="src_ibkr_contract",
            name="IBKR contract/reference",
            provider_kind=DataProviderKind.BROKER_OFFICIAL,
            data_domains=[DataDomain.INSTRUMENT_REFERENCE],
            access_method=DataAccessMethod.BROKER_INTERFACE,
            cost_tier=DataCostTier.BROKER_INCLUDED,
            policy=strict,
            notes_nl="Bron voor instrument referentiegegevens.",
        ),
        DataSourceDefinition(
            data_source_id="src_ibkr_account",
            name="IBKR account/position",
            provider_kind=DataProviderKind.BROKER_OFFICIAL,
            data_domains=[DataDomain.ACCOUNT_POSITION],
            access_method=DataAccessMethod.BROKER_INTERFACE,
            cost_tier=DataCostTier.BROKER_INCLUDED,
            policy=strict,
            notes_nl="Bron voor portefeuille posities en saldo.",
        ),
        DataSourceDefinition(
            data_source_id="src_ibkr_order",
            name="IBKR order/execution",
            provider_kind=DataProviderKind.BROKER_OFFICIAL,
            data_domains=[DataDomain.ORDER_EXECUTION],
            access_method=DataAccessMethod.BROKER_INTERFACE,
            cost_tier=DataCostTier.BROKER_INCLUDED,
            policy=strict,
            notes_nl="Bron voor order- en uitvoeringshistoriek.",
        ),
        DataSourceDefinition(
            data_source_id="src_ibkr_market",
            name="IBKR market data",
            provider_kind=DataProviderKind.BROKER_OFFICIAL,
            data_domains=[DataDomain.MARKET_DATA],
            access_method=DataAccessMethod.BROKER_INTERFACE,
            cost_tier=DataCostTier.PAID,
            policy=limited,
            notes_nl="Marktdata enkel wanneer licentie dit toelaat.",
        ),
        DataSourceDefinition(
            data_source_id="src_sec_edgar",
            name="SEC EDGAR filings",
            provider_kind=DataProviderKind.REGULATOR_OFFICIAL,
            data_domains=[DataDomain.COMPANY_FUNDAMENTAL],
            access_method=DataAccessMethod.PUBLIC_FILE_DOWNLOAD,
            cost_tier=DataCostTier.FREE,
            policy=limited,
            source_url="https://www.sec.gov/edgar",
            notes_nl="Officiële bedrijfsfilings.",
        ),
        DataSourceDefinition(
            data_source_id="src_ecb",
            name="ECB macro and FX",
            provider_kind=DataProviderKind.CENTRAL_BANK_OFFICIAL,
            data_domains=[DataDomain.MACRO_DATA, DataDomain.FX_DATA],
            access_method=DataAccessMethod.PUBLIC_API,
            cost_tier=DataCostTier.FREE,
            policy=limited,
            source_url="https://data.ecb.europa.eu",
            notes_nl="Macro- en wisselkoersdata van ECB.",
        ),
        DataSourceDefinition(
            data_source_id="src_fred",
            name="FRED macro data",
            provider_kind=DataProviderKind.GOVERNMENT_OFFICIAL,
            data_domains=[DataDomain.MACRO_DATA],
            access_method=DataAccessMethod.PUBLIC_API,
            cost_tier=DataCostTier.FREE,
            policy=limited,
            source_url="https://fred.stlouisfed.org",
            notes_nl="Macro-economische reeksen.",
        ),
        DataSourceDefinition(
            data_source_id="src_etf_factsheet",
            name="ETF issuer factsheet",
            provider_kind=DataProviderKind.ISSUER_OFFICIAL,
            data_domains=[DataDomain.ETF_REFERENCE],
            access_method=DataAccessMethod.PUBLIC_FILE_DOWNLOAD,
            cost_tier=DataCostTier.FREE,
            policy=limited,
            notes_nl="Factsheet van uitgevende instelling.",
        ),
        DataSourceDefinition(
            data_source_id="src_kid_kiid",
            name="KID/KIID documents",
            provider_kind=DataProviderKind.ISSUER_OFFICIAL,
            data_domains=[DataDomain.LEGAL_DISCLOSURE],
            access_method=DataAccessMethod.PUBLIC_FILE_DOWNLOAD,
            cost_tier=DataCostTier.FREE,
            policy=limited,
            notes_nl="Essentiële beleggersinformatie.",
        ),
        DataSourceDefinition(
            data_source_id="src_etf_holdings",
            name="ETF holdings files",
            provider_kind=DataProviderKind.ISSUER_OFFICIAL,
            data_domains=[DataDomain.HOLDINGS_DATA],
            access_method=DataAccessMethod.PUBLIC_FILE_DOWNLOAD,
            cost_tier=DataCostTier.FREE,
            policy=limited,
            notes_nl="Samenstelling onderliggende posities.",
        ),
        DataSourceDefinition(
            data_source_id="src_exchange_public",
            name="Exchange public market data",
            provider_kind=DataProviderKind.EXCHANGE_OFFICIAL,
            data_domains=[DataDomain.MARKET_DATA],
            access_method=DataAccessMethod.PUBLIC_API,
            cost_tier=DataCostTier.FREE,
            policy=limited,
            notes_nl="Publieke beursdata indien legaal bruikbaar.",
        ),
        DataSourceDefinition(
            data_source_id="src_press_release",
            name="Official company press releases",
            provider_kind=DataProviderKind.COMPANY_OFFICIAL,
            data_domains=[DataDomain.COMPANY_EVENT],
            access_method=DataAccessMethod.PUBLIC_WEBSITE,
            cost_tier=DataCostTier.FREE,
            policy=limited,
            notes_nl="Officiële bedrijfsberichten.",
        ),
        DataSourceDefinition(
            data_source_id="src_public_news",
            name="Public news sources",
            provider_kind=DataProviderKind.PUBLIC_NEWS,
            data_domains=[DataDomain.NEWS_SIGNAL],
            access_method=DataAccessMethod.PUBLIC_WEBSITE,
            cost_tier=DataCostTier.FREE,
            policy=limited,
            notes_nl="Publiek nieuws niet voor suggestie-eligibiliteit.",
        ),
        DataSourceDefinition(
            data_source_id="src_central_bank_announcement",
            name="Central bank/regulator announcements",
            provider_kind=DataProviderKind.REGULATOR_OFFICIAL,
            data_domains=[DataDomain.MACRO_DATA, DataDomain.POLICY_EVENT],
            access_method=DataAccessMethod.PUBLIC_WEBSITE,
            cost_tier=DataCostTier.FREE,
            policy=limited,
            notes_nl="Aankondigingen met beleidsimpact.",
        ),
        DataSourceDefinition(
            data_source_id="src_manual_input",
            name="Manual input",
            provider_kind=DataProviderKind.MANUAL_INTERNAL,
            data_domains=[DataDomain.MANUAL_OVERRIDE],
            access_method=DataAccessMethod.MANUAL_ENTRY,
            cost_tier=DataCostTier.INTERNAL,
            policy=review,
            notes_nl="Handmatige invoer vereist controle.",
        ),
        DataSourceDefinition(
            data_source_id="src_internal_ledger",
            name="Internal portfolio ledger/calculations",
            provider_kind=DataProviderKind.INTERNAL_SYSTEM,
            data_domains=[DataDomain.ACCOUNT_POSITION, DataDomain.PORTFOLIO_ANALYTICS],
            access_method=DataAccessMethod.INTERNAL_SYSTEM,
            cost_tier=DataCostTier.INTERNAL,
            policy=strict,
            notes_nl="Interne berekeningen voor portefeuille.",
        ),
        DataSourceDefinition(
            data_source_id="src_internal_research",
            name="Internal audit/research outputs",
            provider_kind=DataProviderKind.INTERNAL_SYSTEM,
            data_domains=[DataDomain.RESEARCH_OUTPUT, DataDomain.AUDIT_LOG],
            access_method=DataAccessMethod.INTERNAL_SYSTEM,
            cost_tier=DataCostTier.INTERNAL,
            policy=strict,
            notes_nl="Interne audit- en onderzoeksresultaten.",
        ),
        DataSourceDefinition(
            data_source_id="src_public_website",
            name="Public websites",
            provider_kind=DataProviderKind.PUBLIC_WEBSITE,
            data_domains=[DataDomain.RESEARCH_CONTEXT],
            access_method=DataAccessMethod.PUBLIC_WEBSITE,
            cost_tier=DataCostTier.FREE,
            policy=review,
            notes_nl="Publieke websites eerst reviewen.",
        ),
        DataSourceDefinition(
            data_source_id="src_paid_vendor_future",
            name="Future paid vendor placeholder",
            provider_kind=DataProviderKind.PAID_VENDOR,
            data_domains=[DataDomain.MARKET_DATA, DataDomain.COMPANY_FUNDAMENTAL],
            access_method=DataAccessMethod.VENDOR_API,
            cost_tier=DataCostTier.PAID,
            policy=blocked,
            notes_nl="Placeholder voor latere leverancier.",
        ),
    ]

    requirements = [
        DataSourceRequirement(
            data_source_requirement_id="req_suggestion",
            name="Bronnen voor suggestie",
            data_domain=DataDomain.RESEARCH_OUTPUT,
            use_permission=DataUsePermission.SUGGESTION_ELIGIBILITY,
            freshness_class=DataFreshnessClass.DAILY,
            failure_policy=DataFailurePolicy.BLOCK_OPERATION,
            notes_nl="Geen data kwaliteit of traceerbaarheid betekent geen advies.",
        ),
        DataSourceRequirement(
            data_source_requirement_id="req_valuation",
            name="Bronnen voor waardering",
            data_domain=DataDomain.MARKET_DATA,
            use_permission=DataUsePermission.PORTFOLIO_VALUATION,
            freshness_class=DataFreshnessClass.NEAR_REAL_TIME,
            failure_policy=DataFailurePolicy.BLOCK_OPERATION,
            notes_nl="Portefeuillewaardering blokkeert zonder geldige bron.",
        ),
        DataSourceRequirement(
            data_source_requirement_id="req_research_context",
            name="Context voor onderzoek",
            data_domain=DataDomain.RESEARCH_CONTEXT,
            use_permission=DataUsePermission.RESEARCH_CONTEXT,
            freshness_class=DataFreshnessClass.WEEKLY,
            failure_policy=DataFailurePolicy.WARN_AND_LOG,
            notes_nl="Onderzoek zonder context geeft waarschuwing.",
        ),
    ]

    return DataSourceRegistry(
        data_source_registry_id="registry_default",
        created_at=created_at,
        sources=sources,
        requirements=requirements,
    )
