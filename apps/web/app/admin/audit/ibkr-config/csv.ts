/**
 * V1.2 §BZ vervolg — CSV export helpers voor de IBKR-config audit-trail.
 *
 * Apart bestand omdat Next.js 15 ``page.tsx`` files alleen specifieke
 * named exports toelaat (``default``, ``metadata``, etc.). Een gewone
 * helper-export vanaf ``page.tsx`` gaf:
 *
 *   Type error: Page "app/admin/audit/ibkr-config/page.tsx" does not
 *   match the required types of a Next.js Page.
 *     "buildAuditCsv" is not a valid Page export field.
 *
 * Door het in een sibling-file te zetten kan zowel ``page.tsx`` ALS
 * de unit-test 'em importeren zonder Next's strict-export check te
 * triggeren.
 */

import type { SystemEventSummary } from "@/lib/apiClient";

export function buildAuditCsv(events: SystemEventSummary[]): string {
  const rows: string[][] = [
    [
      "created_at_utc",
      "event_code",
      "severity",
      "status",
      "category",
      "source_service",
      "source_component",
      "title_nl",
      "message_nl",
      // V1.2 §BZ vervolg — timeline columns voor compliance trail.
      "resolved_at_utc",
      "archived_at_utc",
    ],
  ];
  for (const e of events) {
    rows.push([
      e.created_at,
      e.event_code,
      e.severity,
      e.status,
      e.category,
      e.source_service,
      e.source_component,
      e.title_nl,
      e.message_nl,
      e.resolved_at ?? "",
      e.archived_at ?? "",
    ]);
  }
  return rows
    .map((row) =>
      row
        .map((cell) => {
          if (cell == null) return "";
          const escaped = String(cell).replace(/"/g, '""');
          return `"${escaped}"`;
        })
        .join(","),
    )
    .join("\n");
}

export function triggerCsvDownload(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
