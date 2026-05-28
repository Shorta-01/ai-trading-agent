import type { ErrorLogItem } from "@/lib/apiClient";

/**
 * The full, structured error description copied to the clipboard — formatted
 * so it can be pasted straight into Claude Code with enough context to fix.
 */
export function toClaudeCodeText(e: ErrorLogItem): string {
  const lines = [
    "=== Fout uit het AI-trading dashboard ===",
    `id: ${e.system_event_id}`,
    `tijd: ${e.created_at}`,
    `ernst: ${e.severity}`,
    `bron: ${e.source_service} / ${e.source_component}`,
    `code: ${e.event_code}`,
    `bericht: ${e.message_nl}`,
    `technische samenvatting: ${e.technical_summary ?? "(geen)"}`,
    "",
    "stacktrace:",
    e.stack_trace_redacted ?? "(geen)",
  ];
  if (e.redacted_details_json) {
    lines.push("", "context:", JSON.stringify(e.redacted_details_json, null, 2));
  }
  return lines.join("\n");
}
