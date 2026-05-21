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
