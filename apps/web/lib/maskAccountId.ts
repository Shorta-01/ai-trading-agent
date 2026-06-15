/**
 * V1.2 §BZ vervolg — TypeScript mirror van de API-side
 * ``mask_account_id`` (in ``apps/api/src/portfolio_outlook_api/ibkr_connection_read_model.py``).
 *
 * Houdt de 2-char prefix + 4-char suffix; vervangt het midden door
 * ``•••``. Voorbeeld: ``DU1234567`` → ``DU•••4567``.
 *
 * Gebruikt door dashboardpagina's die mogelijk een account_id van de
 * API ontvangen (admin/reconciliation, belasting) zodat operator-
 * facing UI nooit per ongeluk een raw IBKR account-ID toont.
 *
 * Korte IDs (< 6 chars) blijven onaangepast — al kort genoeg om geen
 * reconstructie-risico te vormen.
 */
export function maskAccountId(accountId: string | null | undefined): string | null {
  if (!accountId) return null;
  const text = accountId.trim();
  if (!text) return null;
  if (text.length <= 6) return text;
  const prefix = text.slice(0, 2);
  const suffix = text.slice(-4);
  return `${prefix}•••${suffix}`;
}
