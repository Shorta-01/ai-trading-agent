"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { apiClient, type FreshnessAuditResponse } from "@/lib/apiClient";
import { booleanBlockedLabel, formatDateTime } from "../../auditFormatting";

type FreshnessDetail = FreshnessAuditResponse & { linked_readiness_evaluation_id?: string | null };

export default function Page() {
  const params = useParams<{ freshnessAuditId: string }>();
  const query = useQuery({
    queryKey: ["audit-freshness-audit", params.freshnessAuditId],
    enabled: Boolean(params.freshnessAuditId),
    queryFn: async (): Promise<FreshnessDetail> => {
      const r = await apiClient.getRequestAuditFreshnessAudit(params.freshnessAuditId);
      if (!r.ok) throw new Error("error");
      return r.data as FreshnessDetail;
    },
  });
  const record = query.data ?? null;
  if (query.isLoading) return <main className="page-wrap"><p className="empty-state">Laden...</p></main>;
  if (query.isError || !record) return <main className="page-wrap"><p className="empty-state">API niet bereikbaar.</p></main>;
  return <main className="page-wrap"><Link href="/audit">← Terug naar auditoverzicht</Link><h2>Freshness-audit detail</h2><p className="boundary-notice">Read-only status. Geen runtime-fetch, suggesties, actiedrafts of orders.</p><section className="dashboard-card audit-detail-card"><div className="audit-field-grid"><p><b>ID</b><br />{record.freshness_audit_id}</p><p><b>Status</b><br />{record.freshness_status}</p><p><b>Reason</b><br />{record.reason_code ?? "-"}</p><p><b>Bron timestamp</b><br />{formatDateTime(record.source_timestamp)}</p><p><b>Geëvalueerd</b><br />{formatDateTime(record.evaluated_at)}</p><p><b>safe_for_analysis</b><br />{booleanBlockedLabel(record.safe_for_analysis)}</p></div><div className="cross-link-block"><p>{record.request_log_id ? <Link href={`/audit/request-logs/${record.request_log_id}`}>Open gelinkte request-log</Link> : "Geen gelinkte request-log."}</p><p>{record.provider_source_id ? <Link href={`/audit/provider-sources/${record.provider_source_id}`}>Open gelinkte provider/source metadata</Link> : "Geen gelinkte provider/source metadata."}</p><p>Readiness evaluatie: {record.linked_readiness_evaluation_id ?? "-"}</p></div></section></main>;
}
