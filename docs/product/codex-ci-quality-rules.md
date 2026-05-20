# Codex CI Quality Rules

Doel: herhaalbare CI-fouten voorkomen bij toekomstige Codex-taken.

## Verplichte checklist voor elke taak

1. **Nieuwe Alembic migratie toegevoegd?**  
   Werk alle migratieverwachtingen en inventaris-tests bij:
   - expected revision list
   - expected revision count
   - latest expected revision id
   - metadata expected table set
   - storage status endpoint expectations
   - migration filename inventory tests

2. **Nieuwe tabel toegevoegd?**  
   Controleer en werk bij waar nodig:
   - SQLAlchemy metadata
   - storage exports
   - repository contracts
   - repository implementation
   - metadata tests
   - migration tests
   - `docs/product/version-1-scope-register.md`

3. **Zelfde checks draaien als GitHub CI voor elke geraakte package**
   - `ruff check .`
   - `mypy src`
   - `pytest` (of `pytest -q` waar CI dit gebruikt)

4. **Geen “ready” status zonder lokale verificatie**  
   Als dependencies ontbreken: eerst installeren en testen; anders expliciet melden dat de PR niet geverifieerd is.

5. **Geen brede ruff-ignores als snelle fix**  
   Los terugkerende lintfouten op via correcte formatting/code-aanpassing.
