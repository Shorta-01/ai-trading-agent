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
  const [state, setState] = useState<"loading" | "ok" | "not_found" | "error">("loading");
  useEffect(() => { void (async () => { const r = await apiClient.getRequestAuditRequestLog(params.requestLogId); if (!r.ok) return setState("error"); setRecord(r.data as RequestLogDetail); setState("ok"); })(); }, [params.requestLogId]);
  if (state === "loading") return <main className="page-wrap"><p className="empty-state">Laden...</p></main>;
  if (state === "not_found") return <main className="page-wrap"><p className="empty-state">Record niet gevonden.</p><Link href="/audit">← Terug naar auditoverzicht</Link></main>;
  if (state === "error" || !record) return <main className="page-wrap"><p className="empty-state">API niet bereikbaar.</p><Link href="/audit">← Terug naar auditoverzicht</Link></main>;
  return <main className="page-wrap"><Link href="/audit">← Terug naar auditoverzicht</Link><h2>Request-log detail</h2><p className="boundary-notice">Read-only auditweergave. Deze pagina start geen runtime-fetch en maakt geen suggesties, actiedrafts of orders.</p><section className="dashboard-card audit-detail-card"><div className="audit-field-grid"><p><b>ID</b><br />{record.request_log_id}</p><p><b>Status</b><br />{record.request_status}</p><p><b>Provider</b><br />{record.provider_code}</p><p><b>Domein</b><br />{record.data_domain}</p><p><b>Aangemaakt</b><br />{formatDateTime(record.created_at)}</p><p><b>safe_for_analysis</b><br />{booleanBlockedLabel(record.safe_for_analysis)}</p></div><div className="cross-link-block"><h4>Auditkoppelingen</h4><p>{record.linked_freshness_audit_id ? <Link href={`/audit/freshness-audits/${record.linked_freshness_audit_id}`}>Open gelinkte freshness-audit</Link> : "Geen gelinkte freshness-audit."}</p><p>Readiness evaluatie: {record.linked_readiness_evaluation_id ?? "-"}</p></div></section></main>;
}
