"use client";

/**
 * V1.2 §AU / CLAUDE.md §5 — Beheer-UI voor favorieten en uitsluitingen.
 *
 * Twee tabbladen:
 *   - Favorieten — symbolen waar je extra confidence-uitleg op wilt
 *     zien (dashboard FavorietenWidget).
 *   - Uitsluitingen — symbolen die de orchestrator nooit mag
 *     voorstellen. Harde veto.
 *
 * Geen typing-prompts: toevoegen vraagt symbol + optionele note,
 * verwijderen is één klik per regel. Idempotente backend zorgt dat
 * de UI niet bang hoeft te zijn voor dubbel-klikken.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  apiClient,
  type WatchlistExclusionRow,
  type WatchlistExclusionsResponse,
  type WatchlistFavoriteRow,
  type WatchlistFavoritesResponse,
} from "@/lib/apiClient";

type Tab = "favorieten" | "uitsluitingen" | "hybride";

const FAVORIETEN_KEY = ["watchlist-favorieten-settings"];
const UITSLUITINGEN_KEY = ["watchlist-uitsluitingen-settings"];

function TabButton({
  active,
  label,
  testId,
  onClick,
}: {
  active: boolean;
  label: string;
  testId: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onClick}
      style={{
        padding: "8px 14px",
        background: active ? "#0f172a" : "#e5e7eb",
        color: active ? "#ffffff" : "#374151",
        border: "none",
        borderRadius: 6,
        fontWeight: 600,
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}

function AddForm({
  kind,
  onAdd,
  busy,
  error,
}: {
  kind: "favorite" | "excluded";
  onAdd: (symbol: string, note: string | null) => void;
  busy: boolean;
  error: string | null;
}) {
  const [symbol, setSymbol] = useState("");
  const [note, setNote] = useState("");

  const label =
    kind === "favorite" ? "Voeg favoriet toe" : "Voeg uitsluiting toe";
  const placeholder =
    kind === "favorite" ? "AAPL of ASML.AS" : "TSLA";

  const handleSubmit = () => {
    const trimmed = symbol.trim();
    if (!trimmed) return;
    onAdd(trimmed, note.trim() === "" ? null : note.trim());
    setSymbol("");
    setNote("");
  };

  return (
    <div
      data-testid={`watchlist-${kind}-add-form`}
      style={{
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        alignItems: "flex-end",
        background: "#f9fafb",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 12,
        marginBottom: 12,
      }}
    >
      <div style={{ flex: "1 1 160px" }}>
        <label style={{ display: "block", fontSize: 12, color: "#6b7280" }}>
          Symbool
        </label>
        <input
          data-testid={`watchlist-${kind}-input-symbol`}
          type="text"
          value={symbol}
          placeholder={placeholder}
          onChange={(e) => setSymbol(e.target.value)}
          style={{
            width: "100%",
            padding: "6px 8px",
            border: "1px solid #d1d5db",
            borderRadius: 6,
            fontSize: 13,
          }}
        />
      </div>
      <div style={{ flex: "2 1 220px" }}>
        <label style={{ display: "block", fontSize: 12, color: "#6b7280" }}>
          Notitie (optioneel)
        </label>
        <input
          data-testid={`watchlist-${kind}-input-note`}
          type="text"
          value={note}
          placeholder={
            kind === "favorite"
              ? "Waarom volgen?"
              : "Waarom uitsluiten?"
          }
          onChange={(e) => setNote(e.target.value)}
          style={{
            width: "100%",
            padding: "6px 8px",
            border: "1px solid #d1d5db",
            borderRadius: 6,
            fontSize: 13,
          }}
        />
      </div>
      <button
        type="button"
        data-testid={`watchlist-${kind}-submit`}
        onClick={handleSubmit}
        disabled={busy || symbol.trim() === ""}
        style={{
          padding: "8px 14px",
          background:
            busy || symbol.trim() === "" ? "#9ca3af" : "#15803d",
          color: "#ffffff",
          border: "none",
          borderRadius: 6,
          fontWeight: 600,
          cursor:
            busy || symbol.trim() === "" ? "not-allowed" : "pointer",
        }}
      >
        {busy ? "Bezig…" : label}
      </button>
      {error ? (
        <p
          data-testid={`watchlist-${kind}-error`}
          style={{ flexBasis: "100%", color: "#b91c1c", fontSize: 12, margin: 0 }}
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}

function FavorietenList({
  items,
  onRemove,
  busy,
}: {
  items: WatchlistFavoriteRow[];
  onRemove: (symbol: string) => void;
  busy: boolean;
}) {
  if (items.length === 0) {
    return (
      <p
        data-testid="watchlist-favorieten-empty"
        style={{ color: "#6b7280", fontStyle: "italic", fontSize: 13 }}
      >
        Nog geen favorieten — voeg er één toe hierboven.
      </p>
    );
  }
  return (
    <ul
      data-testid="watchlist-favorieten-list"
      style={{ listStyle: "none", margin: 0, padding: 0 }}
    >
      {items.map((row) => (
        <li
          key={row.watchlist_preference_id}
          data-testid={`watchlist-favorieten-row-${row.symbol}`}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "8px 0",
            borderBottom: "1px solid #f3f4f6",
          }}
        >
          <span style={{ fontWeight: 700, fontSize: 13, minWidth: 90 }}>
            {row.symbol}
          </span>
          <span style={{ fontSize: 12, color: "#6b7280", flex: 1 }}>
            {row.note ?? "—"}
          </span>
          <button
            type="button"
            data-testid={`watchlist-favorieten-remove-${row.symbol}`}
            onClick={() => onRemove(row.symbol)}
            disabled={busy}
            style={{
              padding: "4px 10px",
              background: "#fee2e2",
              color: "#991b1b",
              border: "none",
              borderRadius: 6,
              cursor: busy ? "not-allowed" : "pointer",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            Verwijder
          </button>
        </li>
      ))}
    </ul>
  );
}

function UitsluitingenList({
  items,
  onRemove,
  busy,
}: {
  items: WatchlistExclusionRow[];
  onRemove: (symbol: string) => void;
  busy: boolean;
}) {
  if (items.length === 0) {
    return (
      <p
        data-testid="watchlist-uitsluitingen-empty"
        style={{ color: "#6b7280", fontStyle: "italic", fontSize: 13 }}
      >
        Nog geen uitsluitingen — voeg er één toe hierboven.
      </p>
    );
  }
  return (
    <ul
      data-testid="watchlist-uitsluitingen-list"
      style={{ listStyle: "none", margin: 0, padding: 0 }}
    >
      {items.map((row) => (
        <li
          key={row.watchlist_preference_id}
          data-testid={`watchlist-uitsluitingen-row-${row.symbol}`}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "8px 0",
            borderBottom: "1px solid #f3f4f6",
          }}
        >
          <span style={{ fontWeight: 700, fontSize: 13, minWidth: 90 }}>
            {row.symbol}
          </span>
          <span style={{ fontSize: 12, color: "#6b7280", flex: 1 }}>
            {row.note ?? "—"}
          </span>
          <button
            type="button"
            data-testid={`watchlist-uitsluitingen-remove-${row.symbol}`}
            onClick={() => onRemove(row.symbol)}
            disabled={busy}
            style={{
              padding: "4px 10px",
              background: "#fee2e2",
              color: "#991b1b",
              border: "none",
              borderRadius: 6,
              cursor: busy ? "not-allowed" : "pointer",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            Verwijder
          </button>
        </li>
      ))}
    </ul>
  );
}

export function WatchlistPreferencesSettings() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("favorieten");
  const [favError, setFavError] = useState<string | null>(null);
  const [excError, setExcError] = useState<string | null>(null);

  const favoritesQuery = useQuery({
    queryKey: FAVORIETEN_KEY,
    queryFn: async (): Promise<WatchlistFavoritesResponse | null> => {
      const result = await apiClient.listFavorieten();
      return result.ok ? result.data : null;
    },
  });
  const exclusionsQuery = useQuery({
    queryKey: UITSLUITINGEN_KEY,
    queryFn: async (): Promise<WatchlistExclusionsResponse | null> => {
      const result = await apiClient.listUitsluitingen();
      return result.ok ? result.data : null;
    },
  });

  const saveMutation = useMutation({
    mutationFn: async (input: {
      symbol: string;
      kind: "favorite" | "excluded";
      note: string | null;
    }) => {
      const result = await apiClient.saveWatchlistPreference({
        symbol: input.symbol,
        kind: input.kind,
        note: input.note,
      });
      if (!result.ok) {
        throw new Error("Opslaan mislukt — controleer dat de API draait.");
      }
      return input.kind;
    },
    onSuccess: (kind) => {
      queryClient.invalidateQueries({
        queryKey: kind === "favorite" ? FAVORIETEN_KEY : UITSLUITINGEN_KEY,
      });
      // The orchestrator widget on the dashboard also benefits from a
      // refresh — invalidate it so the next visit shows the new favorite.
      queryClient.invalidateQueries({
        queryKey: ["watchlist-favorieten"],
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (input: {
      symbol: string;
      kind: "favorite" | "excluded";
    }) => {
      const result = await apiClient.deleteWatchlistPreference(input);
      if (!result.ok) {
        throw new Error("Verwijderen mislukt — controleer dat de API draait.");
      }
      return input.kind;
    },
    onSuccess: (kind) => {
      queryClient.invalidateQueries({
        queryKey: kind === "favorite" ? FAVORIETEN_KEY : UITSLUITINGEN_KEY,
      });
      queryClient.invalidateQueries({
        queryKey: ["watchlist-favorieten"],
      });
    },
  });

  const handleAdd = (kind: "favorite" | "excluded") =>
    (symbol: string, note: string | null) => {
      const setError = kind === "favorite" ? setFavError : setExcError;
      setError(null);
      saveMutation.mutate(
        { symbol, kind, note },
        {
          onError: (err) =>
            setError(err instanceof Error ? err.message : "Onbekende fout."),
        },
      );
    };

  const handleRemove = (kind: "favorite" | "excluded") =>
    (symbol: string) => {
      const setError = kind === "favorite" ? setFavError : setExcError;
      setError(null);
      deleteMutation.mutate(
        { symbol, kind },
        {
          onError: (err) =>
            setError(err instanceof Error ? err.message : "Onbekende fout."),
        },
      );
    };

  return (
    <section
      data-testid="watchlist-preferences-settings"
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 10,
        padding: 16,
      }}
    >
      <h3 style={{ marginTop: 0 }}>Watchlist — favorieten &amp; uitsluitingen</h3>
      <p style={{ margin: 0, fontSize: 13, color: "#374151" }}>
        Favorieten verschijnen op het dashboard met live confidence —
        ook als ze de gates niet passeren. Uitsluitingen worden door de
        orchestrator nooit voorgesteld.
      </p>

      <div style={{ display: "flex", gap: 8, margin: "12px 0" }}>
        <TabButton
          active={tab === "favorieten"}
          label="Favorieten"
          testId="watchlist-tab-favorieten"
          onClick={() => setTab("favorieten")}
        />
        <TabButton
          active={tab === "uitsluitingen"}
          label="Uitsluitingen"
          testId="watchlist-tab-uitsluitingen"
          onClick={() => setTab("uitsluitingen")}
        />
        {/* V1.2 §BP / CLAUDE.md §5 — 3e tab: Hybride mode-overzicht. */}
        <TabButton
          active={tab === "hybride"}
          label="Hybride mode"
          testId="watchlist-tab-hybride"
          onClick={() => setTab("hybride")}
        />
      </div>

      {tab === "favorieten" && (
        <div data-testid="watchlist-favorieten-pane">
          <AddForm
            kind="favorite"
            onAdd={handleAdd("favorite")}
            busy={saveMutation.isPending}
            error={favError}
          />
          <FavorietenList
            items={favoritesQuery.data?.items ?? []}
            onRemove={handleRemove("favorite")}
            busy={deleteMutation.isPending}
          />
        </div>
      )}
      {tab === "uitsluitingen" && (
        <div data-testid="watchlist-uitsluitingen-pane">
          <AddForm
            kind="excluded"
            onAdd={handleAdd("excluded")}
            busy={saveMutation.isPending}
            error={excError}
          />
          <UitsluitingenList
            items={exclusionsQuery.data?.items ?? []}
            onRemove={handleRemove("excluded")}
            busy={deleteMutation.isPending}
          />
        </div>
      )}
      {tab === "hybride" && (
        <HybrideModeOverview
          favorites={favoritesQuery.data?.items ?? []}
          exclusions={exclusionsQuery.data?.items ?? []}
        />
      )}
    </section>
  );
}

function HybrideModeOverview({
  favorites,
  exclusions,
}: {
  favorites: WatchlistFavoriteRow[];
  exclusions: WatchlistExclusionRow[];
}) {
  return (
    <div
      data-testid="watchlist-hybride-pane"
      style={{
        background: "#f9fafb",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 12,
      }}
    >
      <h3 style={{ margin: "0 0 8px", fontSize: 14 }}>
        Hybride mode — drie bronnen tegelijk (CLAUDE.md §5)
      </h3>
      <p
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#374151",
          lineHeight: 1.5,
        }}
      >
        De software werkt met drie bronnen tegelijk: een autonome
        universum-scan over ~3500 grote namen, jouw{" "}
        <strong>favorieten</strong> (live confidence-score, ook als ze
        de gates niet passeren), en jouw{" "}
        <strong>uitsluitingen</strong> (worden nooit voorgesteld).
        Wijzigingen aan deze lijsten gelden direct voor de volgende
        sweep.
      </p>
      <div
        data-testid="watchlist-hybride-summary"
        style={{
          display: "flex",
          gap: 16,
          flexWrap: "wrap",
          marginBottom: 12,
        }}
      >
        <div
          data-testid="watchlist-hybride-favorite-count"
          style={{
            padding: "8px 12px",
            background: "#dcfce7",
            color: "#166534",
            borderRadius: 6,
            fontSize: 13,
          }}
        >
          <strong>{favorites.length}</strong> favoriet
          {favorites.length === 1 ? "" : "en"}
        </div>
        <div
          data-testid="watchlist-hybride-excluded-count"
          style={{
            padding: "8px 12px",
            background: "#fee2e2",
            color: "#991b1b",
            borderRadius: 6,
            fontSize: 13,
          }}
        >
          <strong>{exclusions.length}</strong> uitsluiting
          {exclusions.length === 1 ? "" : "en"}
        </div>
      </div>
      <p
        style={{
          margin: 0,
          fontSize: 11,
          color: "#6b7280",
          fontStyle: "italic",
        }}
      >
        Tip: voeg een symbool toe aan je favorieten wanneer je het wilt
        volgen ondanks lagere confidence. Voeg toe aan uitsluitingen
        wanneer je het bewust nooit voorgesteld wilt krijgen (bv.
        sector-aversie, ethiek).
      </p>
    </div>
  );
}
