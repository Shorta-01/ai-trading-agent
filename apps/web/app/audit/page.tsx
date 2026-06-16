"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { apiClient } from "@/lib/apiClient";
import { buildProviderOptions, buildStatusOptions, countFilteredItems, filteredEmptyText, formatDateTime, matchesAuditSearch, safetySummaryLabel } from "./auditFormatting";

export default function AuditPage() {
  const auditQuery = useQuery({
    queryKey: ["audit-overview"],
    queryFn: async () => {
      const [l, s, f] = await Promise.all([
        apiClient.getRequestAuditRequestLogs(),
        apiClient.getRequestAuditProviderSources(),
        apiClient.getRequestAuditFreshnessAudits(),
      ]);
      // All-or-nothing: the original page only renders once every list
      // loads, and otherwise stays on the loading state.
      if (!(l.ok && s.ok && f.ok)) throw new Error("unreachable");
      return { logs: l.data, sources: s.data, freshness: f.data };
    },
  });
  const logs = auditQuery.data?.logs ?? null;
  const sources = auditQuery.data?.sources ?? null;
  const freshness = auditQuery.data?.freshness ?? null;
  const [q, setQ] = useState(""); const [type, setType] = useState("all"); const [provider, setProvider] = useState("all"); const [status, setStatus] = useState("all");
  const providerOptions = useMemo(() => buildProviderOptions([...(logs?.items.map((i) => i.provider_code) ?? []), ...(sources?.items.map((i) => i.provider_code) ?? [])]), [logs, sources]);
  const statusOptions = useMemo(() => buildStatusOptions([...(logs?.items.map((i) => i.request_status) ?? []), ...(freshness?.items.map((i) => i.freshness_status) ?? [])]), [logs, freshness]);
  if (!logs || !sources || !freshness) return <main className="page-wrap"><div className="empty-state">Laden...</div></main>;

  const reset = () => { setQ(""); setType("all"); setProvider("all"); setStatus("all"); };
  const flogs = logs.items.filter((i) => (type === "all" || type === "logs") && (provider === "all" || i.provider_code === provider) && (status === "all" || i.request_status === status) && matchesAuditSearch([i.request_log_id, i.provider_code, i.request_status, i.data_domain], q));
  const fsources = sources.items.filter((i) => (type === "all" || type === "sources") && (provider === "all" || i.provider_code === provider) && matchesAuditSearch([i.provider_source_id, i.provider_code, i.data_domain, i.source_type], q));
  const ffresh = freshness.items.filter((i) => (type === "all" || type === "freshness") && (status === "all" || i.freshness_status === status) && matchesAuditSearch([i.freshness_audit_id, i.request_log_id, i.provider_source_id, i.reason_code, i.data_domain], q));
  const total = logs.total_count + sources.total_count + freshness.total_count;
  const filteredTotal = flogs.length + fsources.length + ffresh.length;

  return <main className="page-wrap"><h2>Audit</h2><p className="audit-help">Read-only records · Deze pagina start geen runtime-fetch · Geen orders</p>
    <div className="audit-toolbar">{/* controls */}
      <input className="audit-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Zoek op ID, provider, status, domein" />
      <select value={type} onChange={(e) => setType(e.target.value)}><option value="all">Alles</option><option value="logs">Request logs</option><option value="sources">Provider sources</option><option value="freshness">Freshness audits</option></select>
      <select value={provider} onChange={(e) => setProvider(e.target.value)}><option value="all">Alle providers</option>{providerOptions.map((i) => <option key={i} value={i}>{i}</option>)}</select>
      <select value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">Alle statussen</option>{statusOptions.map((i) => <option key={i} value={i}>{i}</option>)}</select>
      <button className="reset-button" onClick={reset}>Reset</button>
    </div>
    <div className="audit-summary-cards"><div className="metric-card">Read-only records: {total}</div><div className="metric-card">{safetySummaryLabel("Geblokkeerd voor analyse", logs.blocked_for_analysis_count + freshness.blocked_for_analysis_count)}</div><div className="metric-card">{safetySummaryLabel("Suggesties geblokkeerd", logs.blocked_for_suggestions_count + freshness.blocked_for_suggestions_count)}</div><div className="metric-card">{safetySummaryLabel("Geen actiedrafts", logs.blocked_for_action_drafts_count + freshness.blocked_for_action_drafts_count)}</div></div>
    {total === 0 && <div className="empty-state"><p>Geen records gevonden.</p><p>Deze pagina start geen runtime-fetch.</p><p>Deze pagina maakt geen suggesties, actiedrafts of orders.</p></div>}
    {total > 0 && filteredTotal === 0 && <div className="empty-state"><p>Geen records gevonden.</p><p>{filteredEmptyText()}</p></div>}

    <section className="dashboard-card"><h3>Request logs</h3><p className="filtered-count">{countFilteredItems(flogs.length, logs.items.length)}</p>{flogs.length === 0 ? <p className="fallback-text">Geen records gevonden.</p> : <div className="audit-record-list">{flogs.map((i) => <div className="audit-record-card" key={i.request_log_id}><p>{i.request_log_id}</p><p>{i.provider_code} · {i.request_status} · {i.data_domain}</p><p>{formatDateTime(i.created_at)}</p><Link href={`/audit/request-logs/${i.request_log_id}`}>Open detail</Link></div>)}</div>}</section>
    <section className="dashboard-card"><h3>Provider/source metadata</h3><p className="filtered-count">{countFilteredItems(fsources.length, sources.items.length)}</p>{fsources.length === 0 ? <p className="fallback-text">Geen records gevonden.</p> : <div className="audit-record-list">{fsources.map((i) => <div className="audit-record-card" key={i.provider_source_id}><p>{i.provider_source_id}</p><p>{i.provider_code} · {i.provider_kind} · {i.data_domain} · {i.source_type}</p><Link href={`/audit/provider-sources/${i.provider_source_id}`}>Open detail</Link></div>)}</div>}</section>
    <section className="dashboard-card"><h3>Freshness-audits</h3><p className="filtered-count">{countFilteredItems(ffresh.length, freshness.items.length)}</p>{ffresh.length === 0 ? <p className="fallback-text">Geen records gevonden.</p> : <div className="audit-record-list">{ffresh.map((i) => <div className="audit-record-card" key={i.freshness_audit_id}><p>{i.freshness_audit_id}</p><p>{i.freshness_status} · {i.reason_code ?? "-"} · {i.data_domain}</p><p>{formatDateTime(i.source_timestamp ?? i.evaluated_at)}</p><Link href={`/audit/freshness-audits/${i.freshness_audit_id}`}>Open detail</Link></div>)}</div>}</section>
    {/* V1.2 §BZ vervolg — discoverability: vanaf het overzichts-audit
        scherm naar de IBKR-config audit-trail (mode-switches,
        mismatches, account-id wijzigingen). Eigen page omdat de data
        uit ``system_events`` komt, niet uit de provider-pipeline. */}
    <section className="dashboard-card" data-testid="audit-ibkr-config-card">
      <h3>IBKR-config audit-trail</h3>
      <p className="fallback-text">
        Chronologisch overzicht van mode-switches, account-mismatches en
        account-id wijzigingen — &ldquo;goed huisvader&rdquo;-bewijs voor §12.
      </p>
      <Link
        data-testid="audit-ibkr-config-link"
        href="/admin/audit/ibkr-config"
      >
        Open IBKR-config audit-trail →
      </Link>
    </section>
  </main>;
}
