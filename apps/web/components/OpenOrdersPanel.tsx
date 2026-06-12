"use client";

/**
 * V1.2 §AF — Open orders panel.
 *
 * Pending limit orders sitting at IBKR but not yet filled. Each row
 * shows order id, symbol, side, quantity (filled/remaining), status
 * and last update time. Empty state when nothing is open.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { EmptyState } from "@/components/EmptyState";
import { apiClient, type IbkrOpenOrderSnapshot } from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function Row({ order }: { order: IbkrOpenOrderSnapshot }) {
  return (
    <li
      data-testid={`open-order-row-${order.ibkr_order_id}`}
      style={{
        listStyle: "none",
        padding: "6px 8px",
        marginBottom: 4,
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 6,
        display: "flex",
        alignItems: "center",
        gap: 8,
        fontSize: 12,
      }}
    >
      <span style={{ fontWeight: 700, minWidth: 64 }}>{order.symbol}</span>
      <span style={{ color: "#6b7280" }}>
        {order.action_side ?? "—"} {order.order_type ?? ""}
      </span>
      <span style={{ color: "#374151" }}>
        {order.filled_quantity}/{order.quantity}
      </span>
      <span
        style={{
          background: "#fef3c7",
          color: "#854d0e",
          padding: "1px 6px",
          borderRadius: 8,
          fontSize: 11,
          fontWeight: 600,
        }}
      >
        {order.status}
      </span>
      <span style={{ marginLeft: "auto", color: "#9ca3af", fontSize: 11 }}>
        {order.last_status_at}
      </span>
    </li>
  );
}

export function OpenOrdersPanel() {
  const query = useQuery({
    queryKey: ["open-orders-panel"],
    queryFn: async (): Promise<IbkrOpenOrderSnapshot[]> => {
      const r = await apiClient.getIbkrOpenOrders();
      return r.ok ? (r.data.items ?? []) : [];
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const items = query.data ?? [];

  return (
    <section
      data-testid="open-orders-panel"
      className="dashboard-panel"
      style={{ marginBottom: 12 }}
    >
      <div className="panel-head">
        <h2 style={{ margin: 0, fontSize: 16 }}>Open orders bij IBKR</h2>
        <Link
          href="/portefeuille"
          style={{ fontSize: 12, color: "#1d4ed8", textDecoration: "none" }}
        >
          Detail in portefeuille →
        </Link>
      </div>
      {items.length === 0 ? (
        <EmptyState
          title="Geen open orders"
          message="Limit orders die nog wachten op een fill verschijnen hier."
        />
      ) : (
        <ul style={{ margin: 0, padding: 0 }}>
          {items.slice(0, 8).map((o) => (
            <Row key={o.ibkr_order_id} order={o} />
          ))}
          {items.length > 8 ? (
            <li style={{ listStyle: "none", fontSize: 11, color: "#6b7280" }}>
              +{items.length - 8} meer…
            </li>
          ) : null}
        </ul>
      )}
    </section>
  );
}
