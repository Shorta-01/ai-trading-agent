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
   - public package exports (`__init__.py`)
   - cross-package import checks
   - API `mypy src` wanneer API nieuwe storage-contracten vanuit package-root importeert
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


6. **Nieuwe storage dataclass/record/contract toegevoegd?**  
   - Exporteer het type in `packages/storage/src/ai_trading_agent_storage/__init__.py` wanneer andere packages via de storage package-root importeren.
   - Voeg een public-export smoke test toe of werk die bij (bij voorkeur `packages/storage/tests/test_public_exports.py`).
   - Draai API `mypy src` als de API het nieuwe storage-type importeert.
   - Ga er niet van uit dat storage-tests alleen voldoende zijn; cross-package imports moeten expliciet geverifieerd worden.
   - Een PR is niet ready als API `mypy src` of API `pytest` niet kon draaien door ontbrekende dependencies; installeer dependencies op dezelfde manier als CI en verifieer opnieuw.
