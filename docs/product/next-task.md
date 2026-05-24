# Task 165

Slice 10 — AI explanation layer (RAG read-only). The product locks
require an evidence-grounded AI explanation per suggestion that never
originates a number; it summarises the Decision Package + linked
research evidence in plain Dutch. This slice plugs in the first AI
runtime behind a hard gate: explanations are generated only for
already-persisted Decision Packages, the model is fed the canonical
package JSON + research snippets, and the output is stored as a
read-only `decision_package_explanation` row with the exact source-set
content-hashes captured in a separate `explanation_evidence_ledger`. No
auto-execution; no new financial numbers; safety booleans remain
hard-False on every persisted row. Disabled-by-default; the AI provider
factory returns `None` unless explicitly enabled.
