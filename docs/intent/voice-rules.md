# Voice rules — banned patterns and rationale

**Status:** locked (initial list)
**Locked on:** 2026-05-26
**Version:** 1
**Parent:** `docs/intent/ai-usage.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§13)

## Purpose

This file is the **runtime-readable** banned-patterns list for the voice-and-tone enforcement filter (Layer 2 of `docs/intent/ai-usage.md` §2). The filter loads this file at startup and applies it after every LLM response.

This file is **editable without code changes**. Adding a pattern requires only updating the file and bumping the version field; the filter picks up the new list on next reload.

Hard rule: **patterns are added with rationale; they are never silently removed**. If a pattern is retired, the rationale for the retirement is recorded inline.

## Format

Each entry is a YAML record with:

- `pattern` — exact phrase, regex, or character class.
- `kind` — `phrase` | `regex` | `character`.
- `language` — `en` | `nl` | `any`.
- `action` — `strip` (remove silently) | `rephrase` (replace with neutral alternative) | `fail` (reject the output and trigger fallback).
- `rationale` — one-sentence why this pattern is banned.
- `added_at` — date the pattern was added.

## Version 1 — initial list

```yaml
- pattern: "—"
  kind: character
  language: any
  action: rephrase
  rationale: Em-dash is the strongest tell of LLM-generated text; the project voice uses periods and commas.
  added_at: 2026-05-26

- pattern: "–"
  kind: character
  language: any
  action: rephrase
  rationale: En-dash variant of the em-dash tell; same treatment.
  added_at: 2026-05-26

- pattern: "let me explain"
  kind: phrase
  language: en
  action: strip
  rationale: Filler, conversational tic, adds no information.
  added_at: 2026-05-26

- pattern: "it's important to note"
  kind: phrase
  language: en
  action: strip
  rationale: Filler; the sentence is more direct without it.
  added_at: 2026-05-26

- pattern: "in essence"
  kind: phrase
  language: en
  action: strip
  rationale: Filler; readers know they are reading a summary.
  added_at: 2026-05-26

- pattern: "fundamentally"
  kind: phrase
  language: en
  action: strip
  rationale: Filler adverb that adds no information.
  added_at: 2026-05-26

- pattern: "not just .* but .*"
  kind: regex
  language: en
  action: rephrase
  rationale: Hedge-balance construction characteristic of LLM prose; project voice picks one side.
  added_at: 2026-05-26

- pattern: "\\bunpack\\b"
  kind: regex
  language: en
  action: rephrase
  rationale: Overused LLM verb. Use "explain" or "show".
  added_at: 2026-05-26

- pattern: "\\bdelve\\b"
  kind: regex
  language: en
  action: rephrase
  rationale: Overused LLM verb. Use "examine" or "look at".
  added_at: 2026-05-26

- pattern: "\\bnavigate\\b"
  kind: regex
  language: en
  action: rephrase
  rationale: Banned in the non-literal sense ("navigate this decision"). Literal navigation language is fine.
  added_at: 2026-05-26

- pattern: "\\bleverage\\b"
  kind: regex
  language: en
  action: rephrase
  rationale: Verb usage is jargon. Use "use".
  added_at: 2026-05-26

- pattern: "\\bcrucial\\b"
  kind: regex
  language: en
  action: rephrase
  rationale: Overused intensifier; replace with the specific reason something matters.
  added_at: 2026-05-26

- pattern: "key insight"
  kind: phrase
  language: en
  action: strip
  rationale: Filler. State the insight directly.
  added_at: 2026-05-26

- pattern: "it's worth noting"
  kind: phrase
  language: en
  action: strip
  rationale: Filler. If it's worth noting, say it.
  added_at: 2026-05-26

- pattern: "gedachtestreepje"
  kind: phrase
  language: nl
  action: rephrase
  rationale: Dutch em-dash equivalent in prose; same treatment as em-dash.
  added_at: 2026-05-26

- pattern: "(\\*\\*[^*]+\\*\\*\\s*){3,}"
  kind: regex
  language: any
  action: rephrase
  rationale: More than two bolded spans in a single paragraph is excessive emphasis; voice picks one or two.
  added_at: 2026-05-26
```

## Open questions

- Final initial Dutch banned-patterns list (Dutch-specific patterns to discover from real output) — doctrine §15.

## Cross-references

- `docs/intent/ai-usage.md` (the three-layer enforcement model; this file is layer 2)
- `docs/intent/ai-explanation-prompt.md` (the system prompt; layer 1)
- Doctrine §13 (AI scope)
