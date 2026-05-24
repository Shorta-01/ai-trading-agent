# Task 160

Slice 5 — Decision Package foundation. Persist an immutable, versioned
`AssetDecisionPackageRecord` per (conid, suggestion) that bundles the
upstream evidence chain (position + cash snapshot, market-data + FX
snapshots, forecast, suggestion, gate outcomes) and surface a
`GET /decision-packages/{conid}/latest` plus a Decision Packages section
on the Asset Detail-ready Portefeuille rows. Decision Packages are the
hard prerequisite before any action draft can be created. Disabled-by-default;
no action drafts, no orders.
