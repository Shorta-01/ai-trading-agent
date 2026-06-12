"use client";

/**
 * V1.2 §AG — "Sinds laatste bezoek"-strip.
 *
 * Lichte client-side tracker. Bewaart bij elk bezoek in localStorage
 * - de tijdstempel van het bezoek
 * - de set van verdict-ids die we toen zagen
 * - de set van action-draft-ids die we toen zagen
 *
 * Bij heropening berekent hij de delta met de huidige feeds zodat de
 * operator in 2 seconden ziet of er iets nieuws is. Verdwijnt
 * automatisch als er niks nieuws is.
 *
 * Geen backend nodig; geen broker-promotie pad.
 */

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import {
  apiClient,
  type LatestActionDraftsResponse,
  type OrchestratorVerdictsListResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;
const STORAGE_KEY = "ai-trading-agent:last-visit-v1";

type Snapshot = {
  recorded_at: string;
  verdict_ids: string[];
  draft_ids: string[];
};

function readSnapshot(): Snapshot | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Snapshot;
    if (!Array.isArray(parsed.verdict_ids) || !Array.isArray(parsed.draft_ids))
      return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeSnapshot(snap: Snapshot): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(snap));
  } catch {
    // localStorage may be unavailable (private mode, quota); silent.
  }
}

function formatBrussels(iso: string): string {
  try {
    return new Date(iso).toLocaleString("nl-BE", {
      timeZone: "Europe/Brussels",
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function LastVisitDiffStrip() {
  const verdictsQuery = useQuery({
    queryKey: ["last-visit-verdicts"],
    queryFn: async (): Promise<OrchestratorVerdictsListResponse | null> => {
      const r = await apiClient.listOrchestratorVerdicts({ limit: 200 });
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const draftsQuery = useQuery({
    queryKey: ["last-visit-drafts"],
    queryFn: async (): Promise<LatestActionDraftsResponse | null> => {
      const r = await apiClient.getLatestActionDrafts();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const [previous, setPrevious] = useState<Snapshot | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);

  useEffect(() => {
    setPrevious(readSnapshot());
  }, []);

  const verdictIds = (verdictsQuery.data?.items ?? []).map((v) => v.verdict_id);
  const draftIds = (draftsQuery.data?.items ?? []).map((d) => d.draft_id);
  const loaded = verdictsQuery.isSuccess && draftsQuery.isSuccess;

  const previousVerdicts = new Set(previous?.verdict_ids ?? []);
  const previousDrafts = new Set(previous?.draft_ids ?? []);
  const newVerdicts = previous ? verdictIds.filter((id) => !previousVerdicts.has(id)) : [];
  const newDrafts = previous ? draftIds.filter((id) => !previousDrafts.has(id)) : [];
  const hasDelta = newVerdicts.length > 0 || newDrafts.length > 0;
  const firstVisit = !previous;

  const acknowledge = () => {
    if (!loaded) return;
    writeSnapshot({
      recorded_at: new Date().toISOString(),
      verdict_ids: verdictIds,
      draft_ids: draftIds,
    });
    setPrevious({
      recorded_at: new Date().toISOString(),
      verdict_ids: verdictIds,
      draft_ids: draftIds,
    });
    setAcknowledged(true);
  };

  if (!loaded) return null;
  if (acknowledged) return null;
  if (firstVisit) {
    return (
      <section
        data-testid="last-visit-strip"
        style={{
          background: "#eff6ff",
          border: "1px solid #bfdbfe",
          borderRadius: 8,
          padding: "8px 12px",
          marginBottom: 12,
          display: "flex",
          alignItems: "center",
          gap: 10,
          fontSize: 13,
        }}
      >
        <strong style={{ color: "#1e3a8a" }}>Eerste bezoek vandaag.</strong>
        <span style={{ color: "#1e40af", flex: 1 }}>
          We slaan deze stand op als nullijn — bij je volgende bezoek zie je
          alleen wat erbij gekomen is.
        </span>
        <button
          type="button"
          onClick={acknowledge}
          data-testid="last-visit-strip-baseline"
          style={{
            background: "#1d4ed8",
            color: "white",
            border: "none",
            borderRadius: 6,
            padding: "4px 12px",
            cursor: "pointer",
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          Bewaar nullijn
        </button>
      </section>
    );
  }
  if (!hasDelta) return null;

  return (
    <section
      data-testid="last-visit-strip"
      style={{
        background: "#fef3c7",
        border: "1px solid #fcd34d",
        borderRadius: 8,
        padding: "8px 12px",
        marginBottom: 12,
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontSize: 13,
        flexWrap: "wrap",
      }}
    >
      <strong style={{ color: "#854d0e" }}>
        Sinds {previous ? formatBrussels(previous.recorded_at) : "vorig bezoek"}:
      </strong>
      {newVerdicts.length > 0 ? (
        <span
          data-testid="last-visit-strip-new-verdicts"
          style={{ color: "#854d0e" }}
        >
          {newVerdicts.length} nieuwe verdict{newVerdicts.length === 1 ? "" : "s"}
        </span>
      ) : null}
      {newDrafts.length > 0 ? (
        <span
          data-testid="last-visit-strip-new-drafts"
          style={{ color: "#854d0e" }}
        >
          {newDrafts.length} nieuwe action draft
          {newDrafts.length === 1 ? "" : "s"}
        </span>
      ) : null}
      <button
        type="button"
        onClick={acknowledge}
        data-testid="last-visit-strip-ack"
        style={{
          marginLeft: "auto",
          background: "#92400e",
          color: "white",
          border: "none",
          borderRadius: 6,
          padding: "4px 12px",
          cursor: "pointer",
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        Gezien — markeer als gelezen
      </button>
    </section>
  );
}
