export function ChartPlaceholder({ text }: { text: string }) {
  return (
    <div className="chart-placeholder" role="img" aria-label="Grafiek placeholder">
      <div className="chart-grid" />
      <p>{text}</p>
    </div>
  );
}
