"use client";

/**
 * V1.2 §AZ — operator-aanpasbaar winstdoel.
 *
 * Klein settings-blokje voor /instellingen. Toont de huidige drempel
 * (doctrine-default 4 % of operator-keuze) en biedt een input om te
 * wijzigen. "Reset naar 4 %"-knop zet het terug naar de doctrine.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import {
  apiClient,
  type ProfitTargetResponse,
} from "@/lib/apiClient";

const QUERY_KEY = ["profit-target-setting"];

export function ProfitTargetSetting() {
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async (): Promise<ProfitTargetResponse | null> => {
      const result = await apiClient.getProfitTarget();
      return result.ok ? result.data : null;
    },
  });
  const data = query.data ?? null;

  // Initialize the input from the server response only on the first
  // successful load so manual edits don't get clobbered.
  useEffect(() => {
    if (data !== null && input === "") {
      setInput(data.profit_target_pct);
    }
  }, [data, input]);

  const mutation = useMutation({
    mutationFn: async (next: string | null) => {
      const result = await apiClient.putProfitTarget({
        profit_target_pct: next,
      });
      if (!result.ok) {
        throw new Error("Opslaan mislukt — controleer de waarde.");
      }
      return result.data;
    },
    onSuccess: (resp) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      setSaved(resp.summary_nl);
      setInput(resp.profit_target_pct);
      setError(null);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Onbekende fout.");
      setSaved(null);
    },
  });

  const handleSave = () => {
    setSaved(null);
    setError(null);
    mutation.mutate(input.trim() === "" ? null : input.trim());
  };

  const handleReset = () => {
    setSaved(null);
    setError(null);
    mutation.mutate(null);
  };

  return (
    <section
      data-testid="profit-target-setting"
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 10,
        padding: 16,
      }}
    >
      <h3 style={{ marginTop: 0 }}>Winstdoel per trade (CLAUDE.md §6.1)</h3>
      <p style={{ margin: 0, fontSize: 13, color: "#374151" }}>
        {data?.help_nl ??
          "Operator-aanpasbaar winstdoel voor SELL-suggesties. Default 4 %."}
      </p>
      <p
        data-testid="profit-target-summary"
        style={{ marginTop: 8, fontSize: 13, color: "#374151" }}
      >
        {data?.summary_nl ?? "Laden…"}
      </p>
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: 8,
          marginTop: 12,
          flexWrap: "wrap",
        }}
      >
        <div>
          <label
            style={{ display: "block", fontSize: 12, color: "#6b7280" }}
            htmlFor="profit-target-input"
          >
            Doel %
          </label>
          <input
            id="profit-target-input"
            data-testid="profit-target-input"
            type="text"
            inputMode="decimal"
            value={input}
            placeholder="4"
            onChange={(e) => setInput(e.target.value)}
            style={{
              width: 100,
              padding: "6px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
              fontSize: 13,
            }}
          />
        </div>
        <button
          type="button"
          data-testid="profit-target-save"
          onClick={handleSave}
          disabled={mutation.isPending}
          style={{
            padding: "6px 14px",
            background: mutation.isPending ? "#9ca3af" : "#15803d",
            color: "#ffffff",
            border: "none",
            borderRadius: 6,
            fontWeight: 600,
            cursor: mutation.isPending ? "not-allowed" : "pointer",
            fontSize: 13,
          }}
        >
          {mutation.isPending ? "Bezig…" : "Opslaan"}
        </button>
        <button
          type="button"
          data-testid="profit-target-reset"
          onClick={handleReset}
          disabled={mutation.isPending}
          style={{
            padding: "6px 14px",
            background: "#e5e7eb",
            color: "#374151",
            border: "none",
            borderRadius: 6,
            fontWeight: 600,
            cursor: mutation.isPending ? "not-allowed" : "pointer",
            fontSize: 13,
          }}
        >
          Reset naar 4 %
        </button>
      </div>
      {error ? (
        <p
          data-testid="profit-target-error"
          style={{ marginTop: 8, color: "#b91c1c", fontSize: 12 }}
        >
          {error}
        </p>
      ) : null}
      {saved ? (
        <p
          data-testid="profit-target-saved"
          style={{ marginTop: 8, color: "#166534", fontSize: 12 }}
        >
          {saved}
        </p>
      ) : null}
    </section>
  );
}
