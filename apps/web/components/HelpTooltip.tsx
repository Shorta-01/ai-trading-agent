import { IconButtonWithTooltip } from "@/components/IconButtonWithTooltip";

export function HelpTooltip({ text }: { text: string }) {
  return <IconButtonWithTooltip icon="ⓘ" label="Help" tooltip={text} />;
}
