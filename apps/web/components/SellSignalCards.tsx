"use client";

/**
 * V1.2 §BJ / CLAUDE.md §6.3 — SELL-suggestie kaartjes op het dashboard.
 *
 * Toont de actieve SELL-kaartjes (`action="suggest_sell"` en
 * `dismissed_at IS NULL`) die de sweep heeft gegenereerd. Per kaartje:
 *
 *  - groot headline + symbool + huidige %-return
 *  - signal_kind badge (`take_profit` of `hold_review`)
 *  - forecast-context (p50 + kans op verdere stijging) zodat de
 *    operator kan beslissen al-of-niet langer te wachten
 *  - EUR-equivalent van het verkoop-resultaat (CLAUDE.md §6.1
 *    transparency)
 *  - "Verwijder uit lijst" knop met dismiss-reason input (sticky tot
 *    het signaal materieel verandert)
 *  - "Herevalueer nu" knop (POST /sell-signals/sweep) zodat de
 *    operator handmatig een verse pass kan triggeren
 *
 * CLAUDE.md §2: dit zijn ADVIES-kaartjes. De knoppen "Verkopen nu" /
 * "Houden" doen GEEN automatische orders — ze openen straks (P0-5
 * follow-up) een action-draft flow. Voor V1.2 §BJ blijft "Verwijder
 * uit lijst" de enige actieve operator-knop op de kaart.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  apiClient,
  type SellSignalCardResponse,
  type SellSignalListResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function formatPct(value: string | null): string {
  if (value === null) return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2).replace(".", ",")}%`;
}

function formatEur(value: string | null): string {
  if (value === null) return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return `€${n.toLocaleString("nl-BE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatPrice(value: string, currency: string): string {
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  const sym = currency === "USD" ? "$" : currency === "EUR" ? "€" : `${currency} `;
  return `${sym}${n.toLocaleString("nl-BE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function signalKindLabel(kind: string): string {
  if (kind === "take_profit") return "Take-profit +4 %";
  if (kind === "hold_review") return "6m+ hold-review";
  return kind;
}

function SignalKindBadge({ kind }: { kind: string }) {
  const isTakeProfit = kind === "take_profit";
  return (
    <span
      data-testid="sell-signal-card-kind-badge"
      style={{
        padding: "2px 8px",
        background: isTakeProfit ? "#16a34a" : "#a855f7",
        color: "#ffffff",
        borderRadius: 10,
        fontWeight: 700,
        fontSize: 10,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
      }}
    >
      {signalKindLabel(kind)}
    </span>
  );
}

function CardActions({
  card,
  onDismiss,
  isDismissing,
}: {
  card: SellSignalCardResponse;
  onDismiss: (reason: string) => void;
  isDismissing: boolean;
}) {
  const [reason, setReason] = useState("");
  return (
    <div
      data-testid="sell-signal-card-actions"
      style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}
    >
      <input
        type="text"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Optionele reden (b.v. 'ik wacht op verder rijzen')"
        data-testid={`sell-signal-card-dismiss-reason-${card.card_id}`}
        style={{
          flex: 1,
          minWidth: 200,
          padding: "6px 8px",
          border: "1px solid #d1d5db",
          borderRadius: 4,
          fontSize: 12,
        }}
        disabled={isDismissing}
      />
      <button
        type="button"
        data-testid={`sell-signal-card-dismiss-${card.card_id}`}
        onClick={() => onDismiss(reason)}
        disabled={isDismissing}
        style={{
          padding: "6px 12px",
          background: "#6b7280",
          color: "#ffffff",
          border: "none",
          borderRadius: 4,
          fontSize: 12,
          fontWeight: 600,
          cursor: isDismissing ? "not-allowed" : "pointer",
        }}
      >
        Verwijder uit lijst
      </button>
    </div>
  );
}

function SellSignalCard({
  card,
  onDismiss,
  isDismissing,
}: {
  card: SellSignalCardResponse;
  onDismiss: (cardId: string, reason: string) => void;
  isDismissing: boolean;
}) {
  return (
    <article
      data-testid={`sell-signal-card-${card.card_id}`}
      data-symbol={card.symbol}
      data-kind={card.signal_kind}
      style={{
        background: "#ffffff",
        border: "1px solid #fbbf24",
        borderLeft: "4px solid #f59e0b",
        borderRadius: 8,
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <header
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <strong
            data-testid={`sell-signal-card-headline-${card.card_id}`}
            style={{ fontSize: 14, color: "#1f2937" }}
          >
            {card.headline_nl}
          </strong>
          <SignalKindBadge kind={card.signal_kind} />
        </div>
        <span
          data-testid={`sell-signal-card-return-${card.card_id}`}
          style={{
            padding: "2px 10px",
            background:
              Number(card.current_pct_return) >= 0 ? "#16a34a" : "#dc2626",
            color: "#ffffff",
            borderRadius: 12,
            fontWeight: 700,
            fontSize: 12,
          }}
        >
          {formatPct(card.current_pct_return)}
        </span>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: 8,
          fontSize: 12,
          color: "#374151",
        }}
      >
        <div>
          <div style={{ color: "#6b7280", fontSize: 11 }}>Instap</div>
          <div>{formatPrice(card.entry_price, card.currency)}</div>
        </div>
        <div>
          <div style={{ color: "#6b7280", fontSize: 11 }}>Nu</div>
          <div>{formatPrice(card.current_price, card.currency)}</div>
        </div>
        <div>
          <div style={{ color: "#6b7280", fontSize: 11 }}>Aantal</div>
          <div>{card.quantity}</div>
        </div>
        {card.target_pct !== null && (
          <div>
            <div style={{ color: "#6b7280", fontSize: 11 }}>Target</div>
            <div>{formatPct(card.target_pct)}</div>
          </div>
        )}
        {card.days_held !== null && (
          <div>
            <div style={{ color: "#6b7280", fontSize: 11 }}>Hold</div>
            <div>{card.days_held} dagen</div>
          </div>
        )}
        {card.expected_net_proceeds_eur !== null && (
          <div>
            <div style={{ color: "#6b7280", fontSize: 11 }}>Netto EUR</div>
            <div>{formatEur(card.expected_net_proceeds_eur)}</div>
          </div>
        )}
      </div>

      {(card.short_term_p50 !== null || card.short_term_prob_above_pct !== null) && (
        <div
          data-testid={`sell-signal-card-forecast-${card.card_id}`}
          style={{
            background: "#f9fafb",
            border: "1px solid #e5e7eb",
            borderRadius: 4,
            padding: 8,
            fontSize: 12,
            color: "#374151",
          }}
        >
          <div style={{ color: "#6b7280", fontSize: 11, marginBottom: 2 }}>
            Korte-termijn forecast
            {card.short_term_horizon_days !== null
              ? ` (${card.short_term_horizon_days}d)`
              : ""}
          </div>
          <div>
            {card.short_term_p50 !== null && (
              <span>p50 {formatPrice(card.short_term_p50, card.currency)}</span>
            )}
            {card.short_term_p50 !== null &&
              card.short_term_prob_above_pct !== null && (
                <span> · </span>
              )}
            {card.short_term_prob_above_pct !== null && (
              <span>kans op verdere stijging {formatPct(card.short_term_prob_above_pct)}</span>
            )}
          </div>
        </div>
      )}

      <p
        data-testid={`sell-signal-card-detail-${card.card_id}`}
        style={{
          margin: 0,
          fontSize: 12,
          color: "#4b5563",
          lineHeight: 1.4,
        }}
      >
        {card.detail_nl}
      </p>

      <CardActions
        card={card}
        onDismiss={(reason) => onDismiss(card.card_id, reason)}
        isDismissing={isDismissing}
      />
    </article>
  );
}

export function SellSignalCards() {
  const queryClient = useQueryClient();
  const [dismissingId, setDismissingId] = useState<string | null>(null);
  const [sweepInFlight, setSweepInFlight] = useState(false);

  const query = useQuery({
    queryKey: ["sell-signals"],
    queryFn: async (): Promise<SellSignalListResponse | null> => {
      const result = await apiClient.getSellSignals();
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data;
  const cards = data?.cards ?? [];

  const dismissMutation = useMutation({
    mutationFn: async ({ cardId, reason }: { cardId: string; reason: string }) => {
      setDismissingId(cardId);
      const result = await apiClient.dismissSellSignal(
        cardId,
        reason.trim() === "" ? undefined : reason,
      );
      if (!result.ok) {
        throw new Error(result.message);
      }
      return result.data;
    },
    onSettled: () => {
      setDismissingId(null);
      queryClient.invalidateQueries({ queryKey: ["sell-signals"] });
    },
  });

  const sweepMutation = useMutation({
    mutationFn: async () => {
      setSweepInFlight(true);
      const result = await apiClient.triggerSellSignalSweep();
      if (!result.ok) {
        throw new Error("Kon de sweep niet triggeren.");
      }
      return result.data;
    },
    onSettled: () => {
      setSweepInFlight(false);
      queryClient.invalidateQueries({ queryKey: ["sell-signals"] });
    },
  });

  return (
    <section
      data-testid="sell-signal-cards"
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 12,
        marginBottom: 12,
      }}
    >
      <header
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 8,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: 14, color: "#1f2937" }}>
            {data?.title_nl ?? "SELL-suggesties"}
          </h2>
          <p
            style={{
              margin: "2px 0 0 0",
              fontSize: 11,
              color: "#6b7280",
            }}
          >
            {data?.help_nl ??
              "SELL-suggestie kaartjes. CLAUDE.md §2: dit is advies — operator beslist altijd."}
          </p>
        </div>
        <button
          type="button"
          data-testid="sell-signal-cards-sweep-button"
          onClick={() => sweepMutation.mutate()}
          disabled={sweepInFlight}
          style={{
            padding: "6px 12px",
            background: "#0f172a",
            color: "#ffffff",
            border: "none",
            borderRadius: 4,
            fontSize: 12,
            fontWeight: 600,
            cursor: sweepInFlight ? "not-allowed" : "pointer",
          }}
        >
          {sweepInFlight ? "Herevalueren…" : "Herevalueer nu"}
        </button>
      </header>

      {query.isLoading && (
        <p
          data-testid="sell-signal-cards-loading"
          style={{ margin: 0, fontSize: 12, color: "#6b7280" }}
        >
          SELL-suggesties laden…
        </p>
      )}
      {!query.isLoading && query.data === null && (
        <p
          data-testid="sell-signal-cards-error"
          style={{ margin: 0, fontSize: 12, color: "#dc2626" }}
        >
          Kon SELL-suggesties niet ophalen. Endpoint mogelijk niet bereikbaar.
        </p>
      )}
      {!query.isLoading && data !== null && data !== undefined && cards.length === 0 && (
        <p
          data-testid="sell-signal-cards-empty"
          style={{ margin: 0, fontSize: 12, color: "#6b7280" }}
        >
          Geen actieve SELL-suggesties op dit moment. De software monitort
          door — zodra een positie de +4 % target raakt of na 6+ maanden de
          combo-trigger uitkomt, verschijnt hier een kaartje.
        </p>
      )}
      {cards.length > 0 && (
        <div
          data-testid="sell-signal-cards-list"
          style={{ display: "flex", flexDirection: "column", gap: 8 }}
        >
          {cards.map((card) => (
            <SellSignalCard
              key={card.card_id}
              card={card}
              isDismissing={dismissingId === card.card_id}
              onDismiss={(cardId, reason) =>
                dismissMutation.mutate({ cardId, reason })
              }
            />
          ))}
        </div>
      )}
    </section>
  );
}
