# ai-trading-agent-storage

Dit package is een technische storage-foundation voor AI-Trading-Agent.

## Doel van dit package
- SQLAlchemy/Alembic dependencylaag voorbereiden.
- Eén centrale metadata-target voorzien voor toekomstige migraties.
- Veilige database-url redaction helpers voorzien zonder secrets te tonen.

## Bewuste grenzen in deze fase
- Geen tabellen.
- Geen migratie-revisies.
- Geen persistence van setup/portfolio/transacties/suggesties.
- Geen API- of worker-runtime databaseverbinding.
- Domain en portfolio blijven database-vrij.
- `alembic.ini` bevat enkel een placeholder-url, nooit echte secrets.

## Volgende stap (later)
- Eerste schema-migratie toevoegen voor paper setup en audit foundation.

## Task 24: first schema migration foundation
- Eerste schema-tabellen zijn gedefinieerd in SQLAlchemy Core metadata.
- Eerste Alembic migratie-revisie bestaat nu voor paper setup en audit foundation.
- De app gebruikt de database nog niet in runtime (geen API/worker DB-verbinding).
- First-run setup wordt nog niet gepersisteerd.
- Tabellen zijn alleen storage-foundation mappings, zonder businesslogica.
- Geldkolommen gebruiken Numeric (Decimal-compatibel), geen floattypes.
- Paper-only constraints zijn expliciet op schema-niveau vastgelegd.
- `audit_events` is foundation-only; hash-chain/append-only enforcement volgt later.
