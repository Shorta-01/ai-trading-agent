import type { ReactElement } from "react";
import type { PortfolioValuationReadinessRow } from "@/lib/apiClient";

type Primitive = string | number | boolean | null;

type PositionPlTraceDetailsProps = {
  row: Pick<
    PortfolioValuationReadinessRow,
    | "missing_cost_basis_inputs"
    | "missing_pl_inputs"
    | "cost_basis_input_trace"
    | "unrealized_pl_input_trace"
    | "cost_basis_status_nl"
    | "cost_basis_help_nl"
    | "unrealized_pl_status_nl"
    | "unrealized_pl_help_nl"
    | "conid"
    | "symbol"
    | "currency"
    | "quantity"
    | "average_cost"
    | "last_market_snapshot_id"
    | "market_price_timestamp"
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
  if (Array.isArray(value)) return "Niet direct leesbaar: detaillijst beschikbaar.";
  if (typeof value === "object") return "Niet direct leesbaar: detailobject beschikbaar.";
  return "Niet beschikbaar";
}

function renderTraceSection(title: string, trace: Record<string, unknown> | null, emptyLabel: string): ReactElement {
  const entries = Object.entries(trace ?? {});
  return (
    <div>
      <strong>{title}</strong>
      {entries.length === 0 ? (
        <p>{emptyLabel}</p>
      ) : (
        <ul>
          {entries.map(([key, value]) => (
            <li key={key}>
              <strong>{key}:</strong> {renderUnknownValue(value)}
            </li>
          ))}
        </ul>
      )}
      {trace ? (
        <details>
          <summary>Ruwe auditdata (technisch, geen adviessignaal)</summary>
          <pre>{JSON.stringify(trace, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}

function renderMissingList(items: string[], emptyLabel: string): string {
  if (items.length === 0) return emptyLabel;
  return items.join(", ");
}

function showValue(value: string | null): string {
  return value && value.trim().length > 0 ? value : "Niet beschikbaar";
}

export function PositionPlTraceDetails({ row }: PositionPlTraceDetailsProps) {
  return (
    <details>
      <summary><strong>Details</strong></summary>
      <p>Controle en herkomst van kostbasis en winst/verlies. Alleen opgeslagen gegevens worden getoond; er worden geen waarden berekend in de browser.</p>
      <ul>
        <li><strong>Conid:</strong> {showValue(row.conid)}</li>
        <li><strong>Symbool:</strong> {showValue(row.symbol)}</li>
        <li><strong>Valuta:</strong> {showValue(row.currency)}</li>
        <li><strong>Aantal:</strong> {row.quantity}</li>
        <li><strong>Gemiddelde kost (brokerinput):</strong> {showValue(row.average_cost)}</li>
        <li><strong>Marktsnapshot:</strong> {showValue(row.last_market_snapshot_id)}</li>
        <li><strong>Prijsmoment:</strong> {showValue(row.market_price_timestamp)}</li>
      </ul>

      <h4>Kostbasiscontrole</h4>
      <p><strong>Status:</strong> {row.cost_basis_status_nl}</p>
      <p><strong>Toelichting:</strong> {row.cost_basis_help_nl}</p>
      <p>
        <strong>Ontbrekende kostbasisinvoer:</strong>{" "}
        {renderMissingList(row.missing_cost_basis_inputs, "Geen ontbrekende kostbasisinvoer gevonden")}
      </p>

      <h4>Winst/verliescontrole</h4>
      <p><strong>Status:</strong> {row.unrealized_pl_status_nl}</p>
      <p><strong>Toelichting:</strong> {row.unrealized_pl_help_nl}</p>
      <p>
        <strong>Ontbrekende winst/verliesinvoer:</strong>{" "}
        {renderMissingList(row.missing_pl_inputs, "Geen ontbrekende winst/verliesinvoer gevonden")}
      </p>

      {renderTraceSection("Herkomst kostbasis", row.cost_basis_input_trace, "Geen herkomst kostbasis beschikbaar")}
      {renderTraceSection("Herkomst winst/verlies", row.unrealized_pl_input_trace, "Geen herkomst winst/verlies beschikbaar")}
    </details>
  );
}
