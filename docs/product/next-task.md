# Next Task

## Task 125G — FX snapshot storage contract preflight (document-first, read-only)

Task 125F heeft bevestigd dat er nog geen bruikbaar opgeslagen FX snapshot-opslagcontract bestaat voor valuation readiness. De volgende veilige slice is daarom contract-first preflight:

- definieer document-first het minimale duurzame FX snapshot storagecontract (schema/repository/API-read),
- nog zonder runtime FX fetch,
- nog zonder market-data runtime,
- nog zonder suggesties/action drafts/orders.

Doel: toekomstige implementatie voorbereiden zodat valuation readiness later stored FX pairs veilig kan lezen zonder runtime fetch.
