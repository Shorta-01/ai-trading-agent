# Task 152 — Real manual IBKR paper-only read-only status check

## 1. Purpose
Eerste echte handmatige read-only IBKR statuscontrolepad toevoegen.

## 2-15. Summary
Deze taak voegt een echte handmatige connect/check/disconnect client toe achter expliciete opt-in gates.
Runtime blijft standaard uit; readiness endpoint maakt nooit verbinding.
Geen sync, market data, FX, suggesties, action drafts, orders of broker execution.
Bekende blocker: lokale/CI dependency-install in deze omgeving blokkeert door package index toegang.
Aanbevolen next task: blocker-repair voor ibapi install/CI dependency path.
