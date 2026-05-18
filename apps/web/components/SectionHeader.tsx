import { HelpText } from "@/components/HelpText";

type SectionHeaderProps = {
  title: string;
  helpText: string;
};

export function SectionHeader({ title, helpText }: SectionHeaderProps) {
  return (
    <header className="section-header">
      <h2>{title}</h2>
      <HelpText text={helpText} />
    </header>
  );
}
