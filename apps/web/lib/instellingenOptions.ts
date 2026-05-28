/**
 * Task 138 — shared option metadata for the Instellingen (Settings) page.
 *
 * Kept out of ``app/instellingen/page.tsx`` because a Next.js page module may
 * export ONLY its default component; any extra named export breaks the build.
 *
 * The enum value lists mirror the Python domain enums in
 * ``packages/domain/src/portfolio_outlook_domain/settings.py`` exactly. The
 * Dutch labels are display-only — the ``value`` is what is sent to the API.
 */

export type SelectOption = { value: string; label_nl: string };

export const PORTFOLIO_GOAL_OPTIONS: SelectOption[] = [
  { value: "balanced_growth_risk", label_nl: "Gebalanceerd (groei en risico)" },
  { value: "stable_income", label_nl: "Stabiel inkomen" },
  { value: "long_term_growth", label_nl: "Groei op lange termijn" },
];

export const RISK_LEVEL_OPTIONS: SelectOption[] = [
  { value: "low", label_nl: "Laag" },
  { value: "medium", label_nl: "Gemiddeld" },
  { value: "high", label_nl: "Hoog" },
];

export const ASSET_MIX_OPTIONS: SelectOption[] = [
  { value: "etf_and_stock_mix", label_nl: "Mix van ETF’s en aandelen" },
  { value: "mostly_etfs", label_nl: "Vooral ETF’s" },
  { value: "mostly_stocks", label_nl: "Vooral aandelen" },
];

export const CURRENCY_PREFERENCE_OPTIONS: SelectOption[] = [
  {
    value: "eur_preferred_usd_allowed",
    label_nl: "Euro voorkeur, dollar toegestaan",
  },
  { value: "eur_only", label_nl: "Alleen euro" },
  { value: "usd_only", label_nl: "Alleen dollar" },
];

export const REGION_OPTIONS: SelectOption[] = [
  { value: "global", label_nl: "Wereldwijd" },
  { value: "europe", label_nl: "Europa" },
  { value: "usa", label_nl: "Verenigde Staten" },
  { value: "emerging", label_nl: "Opkomende markten" },
];

export const SECTOR_OPTIONS: SelectOption[] = [
  { value: "technology", label_nl: "Technologie" },
  { value: "healthcare", label_nl: "Gezondheidszorg" },
  { value: "industrials", label_nl: "Industrie" },
  { value: "financials", label_nl: "Financiële sector" },
  { value: "consumer", label_nl: "Consumentengoederen" },
  { value: "energy", label_nl: "Energie" },
  { value: "utilities", label_nl: "Nutsbedrijven" },
];

export const ALLOWED_UNIVERSE_TOGGLES: { key: string; label_nl: string; help_nl: string }[] = [
  {
    key: "allow_etfs",
    label_nl: "ETF’s toestaan",
    help_nl:
      "Het systeem mag ETF’s onderzoeken en gebruiken voor IBKR paper-acties.",
  },
  {
    key: "allow_stocks",
    label_nl: "Aandelen toestaan",
    help_nl:
      "Het systeem mag gewone aandelen onderzoeken en gebruiken voor paper-acties.",
  },
  {
    key: "allow_bond_etfs",
    label_nl: "Obligatie-ETF’s toestaan",
    help_nl: "Het systeem mag obligatie-ETF’s gebruiken voor paper-acties.",
  },
  {
    key: "allow_commodity_etfs",
    label_nl: "Grondstoffen-ETF’s toestaan",
    help_nl: "Het systeem mag grondstoffen-ETF’s gebruiken voor paper-acties.",
  },
  {
    key: "allow_currencies_watch_only",
    label_nl: "Valuta alleen volgen",
    help_nl: "Valuta mogen gevolgd worden, maar niet gekocht of verkocht.",
  },
];

export const RISK_LIMIT_FIELDS: {
  key: keyof import("./apiClient").RiskLimitsUpdateInput;
  label_nl: string;
  help_nl: string;
  decimal: boolean;
  min: number;
}[] = [
  {
    key: "daily_max_approvals",
    label_nl: "Maximaal aantal goedkeuringen per dag",
    help_nl:
      "Hoeveel acties je maximaal per dag mag goedkeuren. Moet groter dan 0 zijn.",
    decimal: false,
    min: 1,
  },
  {
    key: "cooldown_seconds",
    label_nl: "Afkoelperiode (seconden)",
    help_nl:
      "Minimale tijd tussen twee goedkeuringen, om impulsieve acties af te remmen.",
    decimal: false,
    min: 0,
  },
  {
    key: "anti_revenge_window_hours",
    label_nl: "Anti-revenge venster (uren)",
    help_nl:
      "Periode na een verlies waarin extra voorzichtigheid geldt tegen ‘revenge trading’.",
    decimal: false,
    min: 0,
  },
  {
    key: "anti_revenge_loss_threshold_pct",
    label_nl: "Anti-revenge verliesdrempel (%)",
    help_nl:
      "Verliespercentage dat het anti-revenge venster activeert.",
    decimal: true,
    min: 0,
  },
  {
    key: "soft_drawdown_pct",
    label_nl: "Zachte drawdown-drempel (%)",
    help_nl:
      "Daling van de portefeuille waarbij een waarschuwing wordt gegeven.",
    decimal: true,
    min: 0,
  },
  {
    key: "soft_drawdown_window_days",
    label_nl: "Zachte drawdown venster (dagen)",
    help_nl: "Aantal dagen waarover de zachte drawdown wordt gemeten.",
    decimal: false,
    min: 0,
  },
  {
    key: "hard_drawdown_pct",
    label_nl: "Harde drawdown-drempel (%)",
    help_nl:
      "Daling van de portefeuille waarbij nieuwe acties worden geblokkeerd.",
    decimal: true,
    min: 0,
  },
  {
    key: "hard_drawdown_window_days",
    label_nl: "Harde drawdown venster (dagen)",
    help_nl: "Aantal dagen waarover de harde drawdown wordt gemeten.",
    decimal: false,
    min: 0,
  },
  {
    key: "fomo_drift_pct",
    label_nl: "FOMO-drift drempel (%)",
    help_nl:
      "Hoeveel een prijs mag afwijken voordat een aankoop als ‘FOMO’ wordt gemarkeerd.",
    decimal: true,
    min: 0,
  },
];
