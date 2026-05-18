type HelpTextProps = {
  id?: string;
  text: string;
};

export function HelpText({ id, text }: HelpTextProps) {
  return (
    <p id={id} className="help-text">
      <span className="help-text-label">Help:</span> {text}
    </p>
  );
}
