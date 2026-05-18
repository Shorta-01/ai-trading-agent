"""Pure builders for read-only status/settings placeholder endpoints."""

from portfolio_outlook_api.status_models import (
    AiBudgetSection,
    AiUsageSummary,
    DutchLabelsSummary,
    IbkrSettingsSection,
    IntegrationCard,
    IntegrationsSummary,
    OpenAiSettingsSection,
    SecretSafetySection,
    ServiceStatusCard,
    SettingFieldHelp,
    SettingsSummary,
    SystemStatusSummary,
)


def build_system_status_summary() -> SystemStatusSummary:
    services = [
        ServiceStatusCard(
            key="api",
            label_nl="API",
            status_key="active",
            status_nl="Actief",
            help_nl="De API reageert en levert veilige statusinformatie.",
            blocks_suggestions=False,
            last_checked_at=None,
        ),
        ServiceStatusCard(
            key="worker",
            label_nl="Worker",
            status_key="not_active",
            status_nl="Nog niet actief",
            help_nl="Achtergrondtaken draaien nog niet in deze basisversie.",
            blocks_suggestions=True,
            last_checked_at=None,
            action_nl="Later controleren",
        ),
        ServiceStatusCard(
            key="planning",
            label_nl="Planning",
            status_key="not_active",
            status_nl="Nog niet actief",
            help_nl="Planningregels bestaan, maar er draait nog geen echte planner.",
            blocks_suggestions=True,
            last_checked_at=None,
            action_nl="Later controleren",
        ),
        ServiceStatusCard(
            key="data_quality",
            label_nl="Datakwaliteit",
            status_key="not_checked",
            status_nl="Niet gecontroleerd",
            help_nl="Databronnen zijn nog niet live gekoppeld voor kwaliteitscontrole.",
            blocks_suggestions=True,
            last_checked_at=None,
            action_nl="Later controleren",
        ),
        ServiceStatusCard(
            key="ibkr_paper",
            label_nl="IBKR paper",
            status_key="not_configured",
            status_nl="Niet ingesteld",
            help_nl="IBKR paper is nog niet ingesteld en kan nu niet worden gebruikt.",
            blocks_suggestions=True,
            last_checked_at=None,
            action_nl="Instellen",
        ),
        ServiceStatusCard(
            key="openai",
            label_nl="OpenAI",
            status_key="not_configured",
            status_nl="Niet ingesteld",
            help_nl="OpenAI is nog niet ingesteld voor onderzoek of verbruiksmeting.",
            blocks_suggestions=True,
            last_checked_at=None,
            action_nl="Instellen",
        ),
        ServiceStatusCard(
            key="ai_research",
            label_nl="AI onderzoek",
            status_key="blocked",
            status_nl="Geblokkeerd",
            help_nl="AI-onderzoek blijft geblokkeerd zonder geldige OpenAI-instelling.",
            blocks_suggestions=True,
            last_checked_at=None,
        ),
        ServiceStatusCard(
            key="audit_log",
            label_nl="Auditlog",
            status_key="not_active",
            status_nl="Nog niet actief",
            help_nl="De volledige auditstroom is nog niet operationeel gekoppeld.",
            blocks_suggestions=True,
            last_checked_at=None,
        ),
        ServiceStatusCard(
            key="storage",
            label_nl="Opslag",
            status_key="not_configured",
            status_nl="Nog niet ingesteld",
            help_nl=(
                "Opslag staat nog uit; portfolio en auditlog kunnen nog niet worden opgeslagen."
            ),
            blocks_suggestions=True,
            last_checked_at=None,
        ),
        ServiceStatusCard(
            key="backup",
            label_nl="Backup",
            status_key="not_checked",
            status_nl="Niet gecontroleerd",
            help_nl="Backups en restore-tests zijn nog niet actief in deze API-laag.",
            blocks_suggestions=True,
            last_checked_at=None,
            action_nl="Later controleren",
        ),
    ]

    return SystemStatusSummary(
        project_name="AI-Trading-Agent",
        mode="paper_only",
        title_nl="Systeemstatus",
        summary_nl="De basis draait in papermodus zonder live koppelingen.",
        help_nl="Deze status toont alleen veilige placeholders zonder externe calls.",
        paper_only=True,
        can_create_new_suggestions=False,
        suggestion_status_nl="Geblokkeerd",
        suggestion_help_nl=(
            "Nieuwe suggesties blijven geblokkeerd tot services en data actief zijn."
        ),
        services=services,
    )


def build_settings_summary() -> SettingsSummary:
    return SettingsSummary(
        title_nl="Instellingen",
        help_nl="Overzicht van wat later nodig is. Deze API toont geen geheime waarden.",
        ibkr=IbkrSettingsSection(
            label_nl="IBKR",
            status_nl="Niet ingesteld",
            help_nl="IBKR paper-koppeling is nog niet ingesteld in deze basisversie.",
            paper_account_required=True,
            live_order_transmission_allowed=False,
            fields_needed_later=[
                SettingFieldHelp(label_nl="Host", help_nl="Serveradres van IBKR Gateway of TWS."),
                SettingFieldHelp(label_nl="Poort", help_nl="Netwerkpoort voor de IBKR-verbinding."),
                SettingFieldHelp(label_nl="Client ID", help_nl="Unieke client-id voor de sessie."),
                SettingFieldHelp(
                    label_nl="Account ID",
                    help_nl="Jouw paper-accountnummer bij IBKR.",
                ),
                SettingFieldHelp(label_nl="Gateway", help_nl="Keuze tussen Gateway of TWS."),
                SettingFieldHelp(
                    label_nl="Paper account",
                    help_nl="Moet op paper staan; live orders blijven uitgeschakeld.",
                ),
            ],
        ),
        openai=OpenAiSettingsSection(
            label_nl="OpenAI",
            status_nl="Niet ingesteld",
            help_nl="OpenAI-koppeling is nog niet actief en gebruikt nu geen API-sleutel.",
            api_key_configured=False,
            fields_needed_later=[
                SettingFieldHelp(
                    label_nl="API-sleutel",
                    help_nl="Geheime sleutel voor OpenAI, nooit zichtbaar in de UI-output.",
                ),
                SettingFieldHelp(
                    label_nl="Project ID",
                    help_nl="Project-id voor kostenopvolging en afbakening.",
                ),
                SettingFieldHelp(
                    label_nl="Organisatie ID",
                    help_nl="Optionele organisatie-id als je account dit gebruikt.",
                ),
                SettingFieldHelp(
                    label_nl="Standaard researchmodel",
                    help_nl="Model dat standaard voor onderzoek gebruikt wordt.",
                ),
                SettingFieldHelp(
                    label_nl="Goedkoper model",
                    help_nl="Model voor goedkopere taken wanneer kwaliteit volstaat.",
                ),
                SettingFieldHelp(
                    label_nl="Maandbudget",
                    help_nl="Maandlimiet voor geschatte AI-kosten in USD/EUR.",
                ),
            ],
        ),
        ai_budget=AiBudgetSection(
            label_nl="AI-budget",
            status_nl="Niet ingesteld",
            help_nl="Budgetregels zijn nog niet gekoppeld aan echte verbruiksdata.",
        ),
        secret_safety=SecretSafetySection(
            label_nl="Geheimen en veiligheid",
            no_secret_values_returned=True,
            no_secret_values_stored_by_endpoint=True,
            help_nl="Deze endpoint geeft geen geheime waarden terug en slaat zelf niets op.",
        ),
    )


def build_ai_usage_summary() -> AiUsageSummary:
    return AiUsageSummary(
        title_nl="AI-verbruik",
        help_nl="Overzicht blijft leeg tot een echte OpenAI-koppeling en logging actief zijn.",
        usage_available=False,
        input_tokens=None,
        output_tokens=None,
        estimated_cost_usd=None,
        estimated_cost_eur=None,
        actual_cost_usd=None,
        budget_status_nl="Niet ingesteld",
        budget_help_nl="Er is nog geen budgetmeting omdat er geen echte verbruiksbron actief is.",
        source_nl="Nog geen OpenAI-koppeling actief",
        warning_nl=(
            "Echte token- en kostgegevens verschijnen pas na een geldige koppeling en logging."
        ),
    )


def build_integrations_summary() -> IntegrationsSummary:
    return IntegrationsSummary(
        title_nl="Integraties",
        help_nl="Status van koppelingen zonder externe verbindingen of runtime checks.",
        cards=[
            IntegrationCard(
                key="ibkr",
                label_nl="IBKR",
                status_nl="Niet ingesteld",
                help_nl="IBKR paper is nog niet geconfigureerd of verbonden.",
                configured=False,
                connected=False,
                blocks_related_jobs=True,
            ),
            IntegrationCard(
                key="openai",
                label_nl="OpenAI",
                status_nl="Niet ingesteld",
                help_nl="OpenAI staat uit en blokkeert AI-onderzoekstaken.",
                configured=False,
                connected=False,
                blocks_related_jobs=True,
            ),
            IntegrationCard(
                key="data_sources",
                label_nl="Data bronnen",
                status_nl="Nog niet actief",
                help_nl="Bronstrategie bestaat, maar runtime-collectors draaien nog niet.",
                configured=True,
                connected=False,
                blocks_related_jobs=True,
            ),
            IntegrationCard(
                key="scheduler",
                label_nl="Scheduler",
                status_nl="Nog niet actief",
                help_nl="Er is wel een plan, maar geen actieve scheduler-runtime.",
                configured=True,
                connected=False,
                blocks_related_jobs=True,
            ),
            IntegrationCard(
                key="worker",
                label_nl="Worker",
                status_nl="Nog niet actief",
                help_nl="Worker-skelet bestaat, maar echte jobs draaien nog niet.",
                configured=True,
                connected=False,
                blocks_related_jobs=True,
            ),
        ],
    )


def build_dutch_labels_summary() -> DutchLabelsSummary:
    return DutchLabelsSummary(
        labels={
            "dashboard": "Dashboard",
            "system_status": "Systeemstatus",
            "settings": "Instellingen",
            "ibkr": "IBKR",
            "openai": "OpenAI",
            "ai_usage": "AI-verbruik",
            "data_quality": "Datakwaliteit",
            "action_suggestions": "Actiesuggesties",
            "budget": "Budget",
            "not_configured": "Niet ingesteld",
            "active": "Actief",
            "error": "Fout",
            "blocked": "Geblokkeerd",
            "not_active_yet": "Nog niet actief",
        }
    )
