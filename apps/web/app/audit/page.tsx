"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiClient, type FreshnessAuditListResponse, type ProviderSourceListResponse, type RequestLogListResponse } from "@/lib/apiClient";
import { formatDateTime } from "./auditFormatting";

export default function AuditPage() {
  const [logs, setLogs] = useState<RequestLogListResponse | null>(null);
  const [sources, setSources] = useState<ProviderSourceListResponse | null>(null);
  const [freshness, setFreshness] = useState<FreshnessAuditListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { void (async () => {
    const [l, s, f] = await Promise.all([apiClient.getRequestAuditRequestLogs(), apiClient.getRequestAuditProviderSources(), apiClient.getRequestAuditFreshnessAudits()]);
    if (!l.ok || !s.ok || !f.ok) return setError("API niet bereikbaar. Dit scherm blijft read-only.");
    setLogs(l.data); setSources(s.data); setFreshness(f.data);
  })(); }, []);

  return <main className="page-wrap"><h2>Audit</h2><p className="audit-help">Read-only auditweergave. Geen runtime-fetch. Geen analysevrijgave. Suggesties geblokkeerd. Geen actiedrafts. Geen orders.</p>
  {error ? <div className="empty-state"><p>{error}</p></div> : null}
  {!logs || !sources || !freshness ? <div className="empty-state"><p>Laden van auditgegevens...</p></div> : <div className="audit-grid">
    <section className="dashboard-card"><h3>Request logs</h3>{logs.items.length===0?<p>Geen records.</p>:<table className="portfolio-table"><thead><tr><th>ID</th><th>Status</th><th>Provider</th><th>Aangemaakt</th></tr></thead><tbody>{logs.items.map((i)=><tr key={i.request_log_id}><td><Link href={`/audit/request-logs/${i.request_log_id}`}>{i.request_log_id}</Link></td><td>{i.request_status}</td><td>{i.provider_code}</td><td>{formatDateTime(i.created_at)}</td></tr>)}</tbody></table>}</section>
    <section className="dashboard-card"><h3>Provider/source metadata</h3>{sources.items.length===0?<p>Geen records.</p>:<table className="portfolio-table"><thead><tr><th>ID</th><th>Provider</th><th>Bron</th><th>Domein</th></tr></thead><tbody>{sources.items.map((i)=><tr key={i.provider_source_id}><td><Link href={`/audit/provider-sources/${i.provider_source_id}`}>{i.provider_source_id}</Link></td><td>{i.provider_code}</td><td>{i.source_type}</td><td>{i.data_domain}</td></tr>)}</tbody></table>}</section>
    <section className="dashboard-card"><h3>Freshness-audits</h3>{freshness.items.length===0?<p>Geen records.</p>:<table className="portfolio-table"><thead><tr><th>ID</th><th>Status</th><th>Domein</th><th>Geëvalueerd</th></tr></thead><tbody>{freshness.items.map((i)=><tr key={i.freshness_audit_id}><td><Link href={`/audit/freshness-audits/${i.freshness_audit_id}`}>{i.freshness_audit_id}</Link></td><td>{i.freshness_status}</td><td>{i.data_domain}</td><td>{formatDateTime(i.evaluated_at)}</td></tr>)}</tbody></table>}</section>
  </div>}</main>;
}
