# Task 164

Slice 9 — Research Desk runtime. Now that the analyse → suggest → decide
→ submit → reconcile → diary loop is complete and disabled-by-default,
the next slice plugs the Research Desk into the Decision Package
evidence chain: ingest research source uploads (already archived in
`research_source_archive`), extract their text deterministically, run a
heuristic credibility/freshness scoring, surface a per-asset research
snippet in the Decision Package, and let the user attach research items
to a suggestion. Still no AI authoring; the runtime emits *evidence
links* only. Disabled-by-default; no automatic broker execution; safety
booleans remain hard-False on every persisted row.
