type IconButtonWithTooltipProps = {
  icon: string;
  label: string;
  tooltip: string;
};

export function IconButtonWithTooltip({ icon, label, tooltip }: IconButtonWithTooltipProps) {
  return (
    <button type="button" className="icon-button" aria-label={label} title={tooltip}>
      <span aria-hidden>{icon}</span>
    </button>
  );
}
