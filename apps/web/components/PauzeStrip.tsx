"use client";

/**
 * V1.2 §AY / CLAUDE.md §11 — Pauze-modus statusbalk + knop.
 *
 * Eén component bovenaan het dashboard met twee verschijningsvormen:
 *
 *   - Software draait: smal blauw bandje met "Pauzeer"-knop.
 *   - Software gepauzeerd: opvallend oranje bandje met "Software
 *     gepauzeerd sinds DD/MM/YYYY HH:MM" + "Hervat"-knop.
 *
 * De click op Pauzeer/Hervat opent een ConfirmModal (CLAUDE.md §8
 * — geen typing-prompts, twee bewuste klikken). Na bevestiging
 * roept de mutation de POST endpoint aan en invalideert de query.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  apiClient,
  type PauzeStatusResponse,
} from "@/lib/apiClient";

import { ConfirmModal } from "./ConfirmModal";

const POLL_INTERVAL_MS = 60_000;

function formatTimestampNl(iso: string | null): string {
  if (iso === null) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)}/${d.getUTCFullYear()} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
}

export function PauzeStrip() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);

  const query = useQuery({
    queryKey: ["pauze-status"],
    queryFn: async (): Promise<PauzeStatusResponse | null> => {
      const result = await apiClient.getPauzeStatus();
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data ?? null;
  const paused = data?.paused ?? false;

  const mutation = useMutation({
    mutationFn: async (action: "pause" | "resume") => {
      const result =
        action === "pause"
          ? await apiClient.postPauze()
          : await apiClient.postHervat();
      if (!result.ok) {
        throw new Error("Kon de pauze-status niet bijwerken.");
      }
      return result.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pauze-status"] });
    },
  });

  const handleClick = () => setModalOpen(true);
  const handleConfirm = () => {
    mutation.mutate(paused ? "resume" : "pause");
    setModalOpen(false);
  };

  const sinceText = data?.paused_at
    ? formatTimestampNl(data.paused_at)
    : null;

  return (
    <>
      <section
        data-testid="pauze-strip"
        data-paused={paused}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "8px 12px",
          marginBottom: 12,
          background: paused ? "#fed7aa" : "#dbeafe",
          color: paused ? "#7c2d12" : "#1e3a8a",
          border: `1px solid ${paused ? "#fdba74" : "#bfdbfe"}`,
          borderRadius: 6,
          fontSize: 13,
        }}
      >
        <span
          data-testid="pauze-strip-badge"
          style={{
            padding: "2px 8px",
            background: paused ? "#7c2d12" : "#1e3a8a",
            color: paused ? "#fed7aa" : "#dbeafe",
            borderRadius: 10,
            fontWeight: 700,
            fontSize: 11,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}
        >
          {paused ? "Gepauzeerd" : "Draaiend"}
        </span>
        <span
          data-testid="pauze-strip-summary"
          style={{ flex: 1 }}
        >
          {paused && sinceText
            ? `Software gepauzeerd sinds ${sinceText}.`
            : (data?.summary_nl ?? "Pauze-status laden…")}
        </span>
        <button
          type="button"
          data-testid="pauze-strip-button"
          onClick={handleClick}
          disabled={mutation.isPending}
          style={{
            padding: "6px 12px",
            background: paused ? "#16a34a" : "#0f172a",
            color: "#ffffff",
            border: "none",
            borderRadius: 6,
            fontWeight: 600,
            fontSize: 12,
            cursor: mutation.isPending ? "not-allowed" : "pointer",
          }}
        >
          {paused ? "Hervat" : "Pauzeer"}
        </button>
      </section>

      <ConfirmModal
        open={modalOpen}
        title={paused ? "Software hervatten?" : "Software pauzeren?"}
        body={
          paused ? (
            <p style={{ margin: 0 }}>
              De morning-chain start opnieuw met BUY-suggesties. SELL-
              monitoring blijft sowieso draaien.
            </p>
          ) : (
            <p style={{ margin: 0 }}>
              Morning-chain stopt met nieuwe BUY-voorstellen. SELL-
              suggesties blijven verschijnen zodat je geen +4 % winst
              mist. Bestaande posities en orders blijven onaangeroerd.
            </p>
          )
        }
        confirmLabel={paused ? "Ja, hervat" : "Ja, pauzeer"}
        confirmTone={paused ? "primary" : "danger"}
        busy={mutation.isPending}
        onConfirm={handleConfirm}
        onCancel={() => setModalOpen(false)}
        testId="pauze-confirm-modal"
      />
    </>
  );
}
