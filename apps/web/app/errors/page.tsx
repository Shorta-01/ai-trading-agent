"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ErrorLogItem, ErrorLogResponse, apiClient } from "@/lib/apiClient";
import { toClaudeCodeText } from "@/lib/errorCopy";

function asNlDate(value: string) {
  return new Date(value).toLocaleString("nl-NL", { timeZone: "UTC" });
}

export default function ErrorsPage() {
  const [status, setStatus] = useState("");

  const query = useQuery({
    queryKey: ["errors"],
    queryFn: async (): Promise<ErrorLogResponse> => {
      const resp = await apiClient.getErrors();
      if (!resp.ok) throw new Error("Fouten konden niet geladen worden.");
      return resp.data;
    },
  });

  const errors = query.data?.errors ?? [];

  async function onResolve(id: string) {
    const resp = await apiClient.resolveError(id);
    setStatus(resp.ok ? "Fout gemarkeerd als opgelost." : "Actie mislukt.");
    if (resp.ok) await query.refetch();
  }

  async function onDelete(id: string) {
    const resp = await apiClient.deleteError(id);
    setStatus(resp.ok ? "Fout verwijderd." : "Actie mislukt.");
    if (resp.ok) await query.refetch();
  }

  async function onCopy(item: ErrorLogItem) {
    await navigator.clipboard.writeText(toClaudeCodeText(item));
    setStatus("Volledige foutbeschrijving gekopieerd — plak in Claude Code.");
  }

  return (
    <main className="container">
      <h1>Fouten</h1>
      <p>
        Hier zie je alle openstaande fouten. Klik &ldquo;Kopieer voor Claude
        Code&rdquo; om de volledige foutbeschrijving te kopiëren en in Claude
        Code te plakken voor een fix.
      </p>

      <div className="dashboard-card">
        <p>Openstaande fouten: {errors.length}</p>
      </div>

      <button type="button" onClick={() => void query.refetch()}>
        Vernieuwen
      </button>
      {status ? <p data-testid="error-action-status">{status}</p> : null}

      {query.isFetching ? <p>Fouten laden...</p> : null}
      {query.isError ? <p>Fouten konden niet geladen worden.</p> : null}
      {!query.isFetching && !query.isError && errors.length === 0 ? (
        <p>Geen openstaande fouten.</p>
      ) : null}

      <div className="events-list">
        {errors.map((item) => (
          <article key={item.system_event_id} className="dashboard-card">
            <h2>{item.title_nl}</h2>
            <p>
              <strong>Ernst:</strong> {item.severity}
            </p>
            <p>
              <strong>Bron:</strong> {item.source_service} /{" "}
              {item.source_component}
            </p>
            <p>
              <strong>Code:</strong> {item.event_code}
            </p>
            <p>
              <strong>Bericht:</strong> {item.message_nl}
            </p>
            <p>
              <strong>Aangemaakt:</strong> {asNlDate(item.created_at)}
            </p>
            {item.technical_summary ? (
              <p>
                <strong>Technisch:</strong> {item.technical_summary}
              </p>
            ) : null}
            {item.stack_trace_redacted ? (
              <pre className="error-stack">{item.stack_trace_redacted}</pre>
            ) : null}
            <div className="events-actions">
              <button type="button" onClick={() => void onCopy(item)}>
                Kopieer voor Claude Code
              </button>
              <button
                type="button"
                onClick={() => void onResolve(item.system_event_id)}
              >
                Oplossen
              </button>
              <button
                type="button"
                onClick={() => void onDelete(item.system_event_id)}
              >
                Verwijderen
              </button>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
