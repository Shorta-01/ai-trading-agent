# Next Task

## Task 125H — FX snapshot storage schema/repository contract implementation (read-only, no runtime fetch)

Task 125G heeft de document-first contractpreflight afgerond. De volgende veilige implementatieslice is nu smal en storage-first:

- implementeer duurzame FX snapshot storage schema + repositorycontract met tests,
- nog zonder runtime FX/provider fetch,
- nog zonder market-data runtime,
- nog zonder valuation conversion runtime,
- nog zonder suggesties/action drafts/orders.

Doel: een bruikbaar read-only opslagcontract opleveren zodat valuation readiness in een latere taak veilig opgeslagen FX-paren kan consumeren.
