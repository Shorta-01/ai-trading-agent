type HelpTextProps = {
  text: string;
};

export function HelpText({ text }: HelpTextProps) {
  return (
    <p className="help-text" title={text}>
      Help: {text}
    </p>
  );
}
