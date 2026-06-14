"use client";

/**
 * V1.2 §BV / GAPS.md P1-8 — Go-live runbook UI.
 *
 * Consumeert het bestaande `GET /runbook` endpoint (V1.2 §BH) en
 * rendert de checklist als drie groepen (`doctrine_locks` /
 * `provider_config` / `doctrine_features`) met per-item status-badge.
 * Eén samenvattende balk bovenaan toont `ready_for_paper_go_live`
 * + de NL summary-tekst.
 *
 * Read-only — geen mutations. Pollt elke 60s zodat operator wijzigingen
 * in /instellingen ook hier zonder refresh ziet verschijnen.
 */

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import {
  apiClient,
  type RunbookItemResponse,
  type RunbookResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function statusColor(status: string): {
  background: string;
  color: string;
  label: string;
} {
  if (status === "ok")
    return { background: "#16a34a", color: "#ffffff", label: "OK" };
  if (status === "info")
    return { background: "#3b82f6", color: "#ffffff", label: "INFO" };
  if (status === "warning")
    return { background: "#f59e0b", color: "#ffffff", label: "WARNING" };
  if (status === "blocking")
    return { background: "#dc2626", color: "#ffffff", label: "BLOCKING" };
  return { background: "#6b7280", color: "#ffffff", label: status.toUpperCase() };
}

function groupLabel(group: string): string {
  if (group === "doctrine_locks") return "Doctrine-locks (hard vereist)";
  if (group === "provider_config") return "Provider-configuratie";
  if (group === "doctrine_features") return "Doctrine-features";
  return group;
}

function ItemRow({ item }: { item: RunbookItemResponse }) {
  const color = statusColor(item.status);
  return (
    <tr data-testid={`runbook-item-${item.code}`}>
      <td
        style={{
          padding: "8px 12px",
          borderBottom: "1px solid #e5e7eb",
          fontWeight: 600,
          fontSize: 13,
          color: "#1f2937",
          verticalAlign: "top",
        }}
      >
        {item.label_nl}
      </td>
      <td
        style={{
          padding: "8px 12px",
          borderBottom: "1px solid #e5e7eb",
          verticalAlign: "top",
        }}
      >
        <span
          data-testid={`runbook-item-status-${item.code}`}
          style={{
            display: "inline-block",
            padding: "2px 10px",
            background: color.background,
            color: color.color,
            borderRadius: 10,
            fontWeight: 700,
            fontSize: 10,
            letterSpacing: "0.04em",
          }}
        >
          {color.label}
        </span>
      </td>
      <td
        style={{
          padding: "8px 12px",
          borderBottom: "1px solid #e5e7eb",
          fontSize: 12,
          color: "#374151",
          verticalAlign: "top",
        }}
      >
        {item.value_nl}
      </td>
      <td
        style={{
          padding: "8px 12px",
          borderBottom: "1px solid #e5e7eb",
          fontSize: 12,
          color: "#6b7280",
          lineHeight: 1.4,
          verticalAlign: "top",
        }}
      >
        {item.what_it_means_nl}
      </td>
    </tr>
  );
}

function GroupSection({
  group,
  items,
}: {
  group: string;
  items: RunbookItemResponse[];
}) {
  return (
    <section
      data-testid={`runbook-group-${group}`}
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        marginBottom: 16,
        overflow: "hidden",
      }}
    >
      <header
        style={{
          padding: "10px 12px",
          background: "#f9fafb",
          borderBottom: "1px solid #e5e7eb",
        }}
      >
        <h2 style={{ margin: 0, fontSize: 14, color: "#1f2937" }}>
          {groupLabel(group)}
        </h2>
      </header>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "#f9fafb" }}>
            <th
              style={{
                padding: "8px 12px",
                textAlign: "left",
                fontSize: 11,
                color: "#6b7280",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              Item
            </th>
            <th
              style={{
                padding: "8px 12px",
                textAlign: "left",
                fontSize: 11,
                color: "#6b7280",
                fontWeight: 600,
                textTransform: "uppercase",
                width: 100,
              }}
            >
              Status
            </th>
            <th
              style={{
                padding: "8px 12px",
                textAlign: "left",
                fontSize: 11,
                color: "#6b7280",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              Waarde
            </th>
            <th
              style={{
                padding: "8px 12px",
                textAlign: "left",
                fontSize: 11,
                color: "#6b7280",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              Wat het betekent
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <ItemRow key={item.code} item={item} />
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default function RunbookPage() {
  const query = useQuery({
    queryKey: ["runbook"],
    queryFn: async (): Promise<RunbookResponse | null> => {
      const result = await apiClient.getRunbook();
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data;

  const groups = useMemo(() => {
    if (!data) return {};
    const out: Record<string, RunbookItemResponse[]> = {};
    for (const item of data.items) {
      if (!out[item.group]) out[item.group] = [];
      out[item.group].push(item);
    }
    return out;
  }, [data]);

  const groupOrder = [
    "doctrine_locks",
    "provider_config",
    "doctrine_features",
  ];

  return (
    <main
      className="page-wrap"
      data-testid="runbook-page"
      style={{ padding: 16 }}
    >
      <h1 style={{ marginBottom: 8, fontSize: 20 }}>
        {data?.title_nl ?? "Go-live runbook"}
      </h1>
      <p
        style={{
          fontSize: 12,
          color: "#6b7280",
          marginBottom: 16,
          lineHeight: 1.4,
        }}
      >
        {data?.help_nl ??
          "Operator-checklist voor paper-go-live. Elk item heeft een status: ok / info / warning / blocking."}
      </p>

      {query.isLoading && (
        <p
          data-testid="runbook-loading"
          style={{ fontSize: 13, color: "#6b7280" }}
        >
          Runbook laden…
        </p>
      )}
      {!query.isLoading && data === null && (
        <p
          data-testid="runbook-error"
          style={{ fontSize: 13, color: "#dc2626" }}
        >
          Kon runbook niet ophalen. Endpoint mogelijk niet bereikbaar.
        </p>
      )}
      {data !== null && data !== undefined && (
        <>
          <section
            data-testid="runbook-summary"
            data-ready={data.ready_for_paper_go_live}
            style={{
              padding: 12,
              marginBottom: 16,
              background: data.ready_for_paper_go_live ? "#dcfce7" : "#fee2e2",
              border: `1px solid ${
                data.ready_for_paper_go_live ? "#86efac" : "#fca5a5"
              }`,
              borderRadius: 8,
              display: "flex",
              gap: 12,
              alignItems: "center",
            }}
          >
            <span
              data-testid="runbook-summary-badge"
              style={{
                padding: "4px 12px",
                background: data.ready_for_paper_go_live
                  ? "#16a34a"
                  : "#dc2626",
                color: "#ffffff",
                borderRadius: 12,
                fontWeight: 700,
                fontSize: 11,
                letterSpacing: "0.04em",
                textTransform: "uppercase",
                whiteSpace: "nowrap",
              }}
            >
              {data.ready_for_paper_go_live
                ? "Klaar voor paper-go-live"
                : "Nog niet klaar"}
            </span>
            <span
              data-testid="runbook-summary-text"
              style={{
                fontSize: 13,
                color: data.ready_for_paper_go_live ? "#14532d" : "#7f1d1d",
              }}
            >
              {data.summary_nl}
            </span>
          </section>

          {groupOrder.map((group) =>
            groups[group] && groups[group].length > 0 ? (
              <GroupSection
                key={group}
                group={group}
                items={groups[group]}
              />
            ) : null,
          )}
        </>
      )}
    </main>
  );
}
