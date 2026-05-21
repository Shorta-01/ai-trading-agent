"use client";
import { useEffect, useMemo, useState } from "react";
import { apiClient, type FreshnessAuditListResponse, type ProviderSourceListResponse, type RequestLogListResponse } from "@/lib/apiClient";
import { buildProviderOptions, buildStatusOptions, countFilteredItems, formatDateTime, matchesAuditSearch, safetySummaryLabel } from "./auditFormatting";

export default function AuditPage() {
  const [logs, setLogs] = useState<RequestLogListResponse | null>(null); const [sources, setSources] = useState<ProviderSourceListResponse | null>(null); const [freshness, setFreshness] = useState<FreshnessAuditListResponse | null>(null);
  const [q, setQ] = useState(""); const [type, setType] = useState("all"); const [provider, setProvider] = useState("all"); const [status, setStatus] = useState("all");
  useEffect(() => { void (async () => { const [l,s,f]=await Promise.all([apiClient.getRequestAuditRequestLogs(),apiClient.getRequestAuditProviderSources(),apiClient.getRequestAuditFreshnessAudits()]); if(l.ok&&s.ok&&f.ok){setLogs(l.data);setSources(s.data);setFreshness(f.data);} })(); }, []);
  const providerOptions = useMemo(()=> buildProviderOptions([...(logs?.items.map(i=>i.provider_code)??[]),...(sources?.items.map(i=>i.provider_code)??[])]),[logs,sources]);
  const statusOptions = useMemo(()=> buildStatusOptions([...(logs?.items.map(i=>i.request_status)??[]),...(freshness?.items.map(i=>i.freshness_status)??[])]),[logs,freshness]);
  if(!logs||!sources||!freshness) return <main className="page-wrap"><div className="empty-state">Laden...</div></main>;
  const reset = ()=>{setQ("");setType("all");setProvider("all");setStatus("all");};
  const flogs=logs.items.filter(i=>(type==="all"||type==="logs")&&(provider==="all"||i.provider_code===provider)&&(status==="all"||i.request_status===status)&&matchesAuditSearch([i.request_log_id,i.provider_code,i.request_status,i.data_domain],q));
  const fsources=sources.items.filter(i=>(type==="all"||type==="sources")&&(provider==="all"||i.provider_code===provider)&&matchesAuditSearch([i.provider_source_id,i.provider_code,i.data_domain,i.source_type],q));
  const ffresh=freshness.items.filter(i=>(type==="all"||type==="freshness")&&(status==="all"||i.freshness_status===status)&&matchesAuditSearch([i.freshness_audit_id,i.request_log_id,i.provider_source_id,i.reason_code,i.data_domain],q));
  return <main className="page-wrap"><h2>Audit</h2><p className="audit-help">Read-only records · Geen runtime-fetch · Geen orders</p>
  <div className="audit-toolbar"><input className="audit-search" value={q} onChange={(e)=>setQ(e.target.value)} placeholder="Zoek op ID, provider, status, domein"/><select value={type} onChange={(e)=>setType(e.target.value)}><option value="all">Alles</option><option value="logs">Request logs</option><option value="sources">Provider sources</option><option value="freshness">Freshness audits</option></select><select value={provider} onChange={(e)=>setProvider(e.target.value)}><option value="all">Alle providers</option>{providerOptions.map(i=><option key={i} value={i}>{i}</option>)}</select><select value={status} onChange={(e)=>setStatus(e.target.value)}><option value="all">Alle statussen</option>{statusOptions.map(i=><option key={i} value={i}>{i}</option>)}</select><button className="reset-button" onClick={reset}>Reset</button></div>
  <div className="audit-summary-cards"><div className="metric-card">Read-only records: {logs.total_count+sources.total_count+freshness.total_count}</div><div className="metric-card">{safetySummaryLabel("Geblokkeerd voor analyse", logs.blocked_for_analysis_count+freshness.blocked_for_analysis_count)}</div><div className="metric-card">{safetySummaryLabel("Suggesties geblokkeerd", logs.blocked_for_suggestions_count+freshness.blocked_for_suggestions_count)}</div><div className="metric-card">{safetySummaryLabel("Geen actiedrafts", logs.blocked_for_action_drafts_count+freshness.blocked_for_action_drafts_count)}</div><div className="metric-card">Geen orders</div><div className="metric-card">Geen runtime-fetch</div></div>
  <section className="dashboard-card"><h3>Request logs</h3><p className="filtered-count">{countFilteredItems(flogs.length, logs.items.length)}</p></section>
  <section className="dashboard-card"><h3>Provider/source metadata</h3><p className="filtered-count">{countFilteredItems(fsources.length, sources.items.length)}</p></section>
  <section className="dashboard-card"><h3>Freshness-audits</h3><p className="filtered-count">{countFilteredItems(ffresh.length, freshness.items.length)}</p></section></main>;
}
