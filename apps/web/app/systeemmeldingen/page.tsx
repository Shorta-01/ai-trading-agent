"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ActiveSystemEventsResponse, SystemEventSummary, apiClient } from "@/lib/apiClient";

function asNlDate(value: string) {
  return new Date(value).toLocaleString("nl-NL", { timeZone: "UTC" });
}

function highestSeverity(events: SystemEventSummary[]): string {
  if (events.some((event) => event.severity === "critical" || event.severity === "error")) return "Fout";
  if (events.some((event) => event.severity === "warning")) return "Waarschuwing";
  return "Info";
}

function toCopyText(event: SystemEventSummary): string {
  return [
    `system_event_id: ${event.system_event_id}`,
    `created_at: ${event.created_at}`,
    `severity: ${event.severity}`,
    `category: ${event.category}`,
    `source_service: ${event.source_service}`,
    `source_component: ${event.source_component}`,
    `event_code: ${event.event_code}`,
    `title_nl: ${event.title_nl}`,
    `message_nl: ${event.message_nl}`,
    `help_nl: ${event.help_nl}`,
    `blocks_suggestions: ${event.blocks_suggestions}`,
    `blocks_writes: ${event.blocks_writes}`,
    `blocks_ai_explanation: ${event.blocks_ai_explanation}`,
    `status: ${event.status}`,
    "Technische details zijn nog niet beschikbaar in deze versie.",
  ].join("\n");
}

export default function SysteemmeldingenPage() {
  const [actionStatus, setActionStatus] = useState<string>("");

  const query = useQuery({
    queryKey: ["active-system-events"],
    queryFn: async (): Promise<ActiveSystemEventsResponse> => {
      const response = await apiClient.getActiveSystemEvents();
      if (!response.ok) {
        throw new Error("Systeemmeldingen konden niet geladen worden.");
      }
      return response.data;
    },
  });

  const eventsResponse = query.data ?? null;
  const events = eventsResponse?.events ?? [];

  async function onResolve(systemEventId: string) {
    const response = await apiClient.resolveSystemEvent(systemEventId, { reason_nl: "Gemarkeerd als opgelost vanuit de webinterface." });
    if (!response.ok) {
      setActionStatus("Systeemmeldingen konden niet geladen worden.");
      return;
    }
    setActionStatus("Systeemmelding gemarkeerd als opgelost.");
    await query.refetch();
  }

  async function onArchive(systemEventId: string) {
    const response = await apiClient.archiveSystemEvent(systemEventId, { reason_nl: "Gearchiveerd vanuit de webinterface." });
    if (!response.ok) {
      setActionStatus("Systeemmeldingen konden niet geladen worden.");
      return;
    }
    setActionStatus("Systeemmelding gearchiveerd.");
    await query.refetch();
  }

  async function onCopyDetails(event: SystemEventSummary) {
    await navigator.clipboard.writeText(toCopyText(event));
    setActionStatus("Details gekopieerd.");
  }

  return (
    <main className="container">
      <h1>Systeemmeldingen</h1>
      <p>Hier zie je belangrijke fouten, waarschuwingen en blokkeringen van het systeem.</p>
      <p className="help-text">Help: Bekijk actieve systeemmeldingen.</p>

      <div className="events-summary dashboard-card">
        <p>Actief: {events.length}</p>
        <p>Hoogste ernst: {highestSeverity(events)}</p>
        {eventsResponse?.storage_available === false ? <p>Opslag is momenteel niet beschikbaar.</p> : null}
      </div>

      <button type="button" onClick={() => void query.refetch()}>Vernieuwen</button>
      {actionStatus ? <p>{actionStatus}</p> : null}

      {query.isFetching ? <p>Systeemmeldingen laden...</p> : null}
      {query.isError ? <p>Systeemmeldingen konden niet geladen worden.</p> : null}
      {!query.isFetching && !query.isError && events.length === 0 ? <p>Geen actieve systeemmeldingen.</p> : null}

      <div className="events-list">
        {events.map((event) => (
          <article key={event.system_event_id} className="dashboard-card">
            <h2>{event.title_nl}</h2>
            <p><strong>Ernst:</strong> {event.severity}</p>
            <p><strong>Categorie:</strong> {event.category}</p>
            <p><strong>Bron:</strong> {event.source_service} / {event.source_component}</p>
            <p><strong>Code:</strong> {event.event_code}</p>
            <p><strong>Melding:</strong> {event.message_nl}</p>
            <p><strong>Wat betekent dit?</strong> {event.help_nl}</p>
            <p><strong>Aangemaakt:</strong> {asNlDate(event.created_at)}</p>
            <p><strong>Blokkeert suggesties:</strong> {event.blocks_suggestions ? "Ja" : "Nee"}</p>
            <p><strong>Blokkeert schrijven:</strong> {event.blocks_writes ? "Ja" : "Nee"}</p>
            <p><strong>Blokkeert AI-uitleg:</strong> {event.blocks_ai_explanation ? "Ja" : "Nee"}</p>
            <p><strong>Status:</strong> {event.status}</p>
            <div className="events-actions">
              <button type="button" onClick={() => void onResolve(event.system_event_id)}>Oplossen</button>
              <button type="button" onClick={() => void onArchive(event.system_event_id)}>Archiveren</button>
              <button type="button" onClick={() => void onCopyDetails(event)}>Details kopiëren</button>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
