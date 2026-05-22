import type { ReactElement } from "react";
import { PortfolioValuationReadinessResponse } from "@/lib/apiClient";

type Primitive = string | number | boolean | null;

type ValuationTraceDetailsProps = {
  readiness: Pick<
    PortfolioValuationReadinessResponse,
    | "valuation_input_trace"
    | "missing_total_value_inputs"
    | "missing_market_data_conids"
    | "missing_cash_inputs"
    | "missing_fx_pairs"
    | "stale_fx_pairs"
    | "invalid_fx_pairs"
  >;
};

function isPrimitiveValue(value: unknown): value is Primitive {
  return value === null || ["string", "number", "boolean"].includes(typeof value);
}

function stringifyPrimitive(value: Primitive): string {
  return value === null ? "null" : String(value);
}

function renderUnknownValue(value: unknown): string {
  if (isPrimitiveValue(value)) return stringifyPrimitive(value);
  if (Array.isArray(value) && value.every(isPrimitiveValue)) {
    return value.map((item) => stringifyPrimitive(item)).join(", ");
  }
  if (Array.isArray(value)) return "Detaillijst beschikbaar";
  if (typeof value === "object") return "Detailobject beschikbaar";
  return "Niet beschikbaar";
}

function hasBlockers(readiness: ValuationTraceDetailsProps["readiness"]): boolean {
  return [
    readiness.missing_total_value_inputs,
    readiness.missing_market_data_conids,
    readiness.missing_cash_inputs,
    readiness.missing_fx_pairs,
    readiness.stale_fx_pairs,
    readiness.invalid_fx_pairs,
  ].some((items) => items.length > 0);
}

function renderBlockerSection(label: string, items: string[]): ReactElement | null {
  if (items.length === 0) return null;
  return (
    <li>
      <strong>{label}:</strong> {items.join(", ")}
    </li>
  );
}

export function ValuationTraceDetails({ readiness }: ValuationTraceDetailsProps) {
  const traceEntries = Object.entries(readiness.valuation_input_trace ?? {});

  return (
    <details style={{ marginTop: "1rem" }}>
      <summary><strong>Controle en herkomst</strong></summary>
      <p style={{ marginTop: "0.5rem" }}>
        Hier zie je waarom de totaalwaarde wel of niet veilig getoond wordt en uit welke opgeslagen gegevens de waardering komt.
      </p>

      <h4>Blokkerende details</h4>
      {hasBlockers(readiness) ? (
        <ul>
          {renderBlockerSection("Ontbrekende invoer", readiness.missing_total_value_inputs)}
          {renderBlockerSection("Marktdata ontbreekt", readiness.missing_market_data_conids)}
          {renderBlockerSection("Cashsnapshot ontbreekt", readiness.missing_cash_inputs)}
          {renderBlockerSection("Wisselkoers ontbreekt", readiness.missing_fx_pairs)}
          {renderBlockerSection("Wisselkoers verouderd", readiness.stale_fx_pairs)}
          {renderBlockerSection("Wisselkoers ongeldig", readiness.invalid_fx_pairs)}
        </ul>
      ) : (
        <p>Geen blokkerende detailmeldingen gevonden.</p>
      )}

      <h4>Trace van invoer</h4>
      {traceEntries.length === 0 ? (
        <p>Geen tracegegevens beschikbaar.</p>
      ) : (
        <ul>
          {traceEntries.map(([key, value]) => (
            <li key={key}>
              <strong>{key}:</strong> {renderUnknownValue(value)}
            </li>
          ))}
        </ul>
      )}

      {readiness.valuation_input_trace ? (
        <details>
          <summary>Ruwe auditdata</summary>
          <pre>{JSON.stringify(readiness.valuation_input_trace, null, 2)}</pre>
        </details>
      ) : null}
    </details>
  );
}
