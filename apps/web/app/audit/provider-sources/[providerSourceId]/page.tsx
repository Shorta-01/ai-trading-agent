"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiClient, type ProviderSourceResponse } from "@/lib/apiClient";
import { formatDateTime } from "../../auditFormatting";

export default function Page() {
  const params = useParams<{ providerSourceId: string }>();
  const query = useQuery({
    queryKey: ["audit-provider-source", params.providerSourceId],
    enabled: Boolean(params.providerSourceId),
    queryFn: async (): Promise<ProviderSourceResponse> => {
      const r = await apiClient.getRequestAuditProviderSource(params.providerSourceId);
      if (!r.ok) throw new Error("error");
      return r.data;
    },
  });
  const record = query.data ?? null;
  if (query.isLoading) return <main className="page-wrap"><p className="empty-state">Laden...</p></main>;
  if (query.isError || !record) return <main className="page-wrap"><p className="empty-state">API niet bereikbaar.</p></main>;
  return <main className="page-wrap"><Link href="/audit">← Terug naar auditoverzicht</Link><h2>Provider/source detail</h2><p className="boundary-notice">Metadata/status-only. Geen connectie of fetchgedrag.</p><section className="dashboard-card audit-detail-card"><div className="audit-field-grid"><p><b>ID</b><br />{record.provider_source_id}</p><p><b>Provider</b><br />{record.provider_code}</p><p><b>Domein</b><br />{record.data_domain}</p><p><b>Disabled op</b><br />{formatDateTime(record.disabled_at ?? null)}</p><p><b>Disabled reden</b><br />{record.disabled_reason ?? "Geen disabled-status in huidig storagecontract."}</p></div></section></main>;
}
