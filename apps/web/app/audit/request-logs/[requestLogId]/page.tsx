"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiClient, type RequestLogResponse } from "@/lib/apiClient";
import { booleanBlockedLabel, formatDateTime } from "../../auditFormatting";

type RequestLogDetail = RequestLogResponse & { linked_freshness_audit_id?: string | null; linked_readiness_evaluation_id?: string | null };

export default function Page() {
  const params = useParams<{ requestLogId: string }>();
  const [record, setRecord] = useState<RequestLogDetail | null>(null);
  const [state, setState] = useState("loading");
  useEffect(() => { void (async () => { const result = await apiClient.getRequestAuditRequestLog(params.requestLogId); if (!result.ok) return setState("error"); setRecord(result.data as RequestLogDetail); setState("ok"); })(); }, [params.requestLogId]);
  if (state === "loading") return <main className="page-wrap"><p className="empty-state">Laden...</p></main>;
  if (state !== "ok" || !record) return <main className="page-wrap"><p className="empty-state">Niet gevonden of API niet bereikbaar.</p></main>;
  return <main className="page-wrap"><Link href="/audit">← Terug naar auditoverzicht</Link><h2>Request-log detail</h2><p className="audit-help">Read-only auditweergave · Geen runtime-fetch · Geen analysevrijgave · Suggesties geblokkeerd · Geen actiedrafts · Geen orders</p><section className="dashboard-card audit-detail-card"><div className="audit-field-grid"><p><b>ID</b><br/>{record.request_log_id}</p><p><b>Correlatie</b><br/>{record.correlation_id}</p><p><b>Provider</b><br/>{record.provider_code}</p><p><b>Status</b><br/>{record.request_status}</p><p><b>Aangemaakt</b><br/>{formatDateTime(record.created_at)}</p><p><b>Voltooid</b><br/>{formatDateTime(record.completed_at)}</p><p><b>Domein</b><br/>{record.data_domain}</p><p><b>Target</b><br/>{record.request_target}</p><p><b>safe_for_analysis</b><br/>{booleanBlockedLabel(record.safe_for_analysis)}</p><p><b>safe_for_suggestions</b><br/>{booleanBlockedLabel(record.safe_for_suggestions)}</p><p><b>safe_for_action_drafts</b><br/>{booleanBlockedLabel(record.safe_for_action_drafts)}</p></div><div className="cross-link-block"><h4>Auditkoppelingen</h4><div><p>{record.linked_freshness_audit_id ? <Link href={`/audit/freshness-audits/${record.linked_freshness_audit_id}`}>Open gelinkte freshness-audit</Link> : "Geen freshness-link"}</p><p>Readiness evaluatie: {record.linked_readiness_evaluation_id ?? "-"}</p><p>Provider metadata kan je bekijken op de provider/source pagina.</p></div></div></section></main>;
}
