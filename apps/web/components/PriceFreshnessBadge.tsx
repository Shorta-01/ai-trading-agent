/**
 * Task 129: per-row price-freshness indicator.
 *
 * Three locked visual states matching the API's display-time
 * freshness derivation:
 *
 * * ``fresh`` (green) — "Vers"
 * * ``stale`` (amber) — "Verouderd"
 * * ``unavailable`` (grey) — "Niet beschikbaar"
 */

type Props = {
  readonly freshness: "fresh" | "stale" | "unavailable";
};

const VISUALS: Record<Props["freshness"], { background: string; color: string; label: string }> = {
  fresh: {
    background: "#15803d",
    color: "#ffffff",
    label: "Vers",
  },
  stale: {
    background: "#f59e0b",
    color: "#1f2937",
    label: "Verouderd",
  },
  unavailable: {
    background: "#6b7280",
    color: "#ffffff",
    label: "Niet beschikbaar",
  },
};

export function PriceFreshnessBadge({ freshness }: Props) {
  const visuals = VISUALS[freshness];
  return (
    <span
      data-testid="price-freshness-badge"
      data-state={freshness}
      role="status"
      aria-label={`Prijs-versheid: ${visuals.label}`}
      style={{
        background: visuals.background,
        color: visuals.color,
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        display: "inline-block",
      }}
    >
      {visuals.label}
    </span>
  );
}
