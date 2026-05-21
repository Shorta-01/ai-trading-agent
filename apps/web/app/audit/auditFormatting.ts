export const formatDateTime = (value: string | null | undefined): string => {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("nl-NL");
};

export const displayValue = (value: string | number | boolean | null | undefined): string => {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Ja" : "Nee";
  return String(value);
};

export const booleanBlockedLabel = (value: boolean): string => (value ? "Nee" : "Geblokkeerd (false)");
export const linkedIdLabel = (value: string | null | undefined, fallback: string): string => value ?? fallback;
export const recordTypeLabel = (value: "logs" | "sources" | "freshness"): string => ({ logs: "Request logs", sources: "Provider/source metadata", freshness: "Freshness-audits" })[value];
export const filteredEmptyText = (): string => "Pas je zoekterm of filter aan.";

export const matchesAuditSearch = (tokens: Array<string | null | undefined>, q: string): boolean =>
  !q || tokens.some((v) => (v ?? "").toLowerCase().includes(q.toLowerCase()));

export const buildProviderOptions = (values: string[]): string[] => [...new Set(values.filter(Boolean))].sort();
export const buildStatusOptions = (values: string[]): string[] => [...new Set(values.filter(Boolean))].sort();
export const countFilteredItems = (count: number, total: number): string => `${count} van ${total} records getoond`;
export const safetySummaryLabel = (label: string, value: number): string => `${label}: ${value}`;
