"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import {
  apiClient,
  archiveWatchlistItem,
  createWatchlistItem,
  getMarketDataLatestSnapshotStatus,
  importIbkrWatchlist,
  listIbkrWatchlistInstruments,
  listIbkrWatchlists,
  listWatchlistItems,
  searchIbkrContracts,
  type ForecastByAccountRow,
  type IbkrContractCandidate,
  type IbkrWatchlistInstrument,
  type IbkrWatchlistSummary,
  type WatchlistConfirmationStateResponse,
  type WatchlistItemResponse,
} from "@/lib/apiClient";
import { ForecastExplanationPanel } from "@/components/ForecastExplanationPanel";
import { StatusBadge } from "@/components/StatusBadge";
import { VolglijstColdStartFlow } from "@/components/VolglijstColdStartFlow";

// Volglijst is a pure tracking surface as of the suggestions-grid
// cleanup: it lists assets the operator follows + the latest forecast
// band/probabilities for each, but no action labels and no
// "Maak actie" button. Actionable suggestions live exclusively on
// /suggesties so the two pages have non-overlapping roles.

export default function Page() {
  const confirmationQuery = useQuery({
    queryKey: ["watchlist-confirmation-state-page"],
    queryFn: async (): Promise<WatchlistConfirmationStateResponse | null> => {
      const result = await apiClient.getWatchlistConfirmationState();
      return result.ok ? result.data : null;
    },
  });
  const confirmationState = confirmationQuery.data ?? null;
  const confirmationLoaded = !confirmationQuery.isPending;

  if (!confirmationLoaded) {
    return (
      <main className="page-wrap" data-testid="volglijst-loading">
        <p>Bezig met laden…</p>
      </main>
    );
  }

  if (confirmationState?.state === "unconfirmed") {
    return (
      <VolglijstColdStartFlow
        onConfirmed={() => void confirmationQuery.refetch()}
      />
    );
  }

  return <VolglijstConfirmedView />;
}

type WatchlistViewData = {
  items: WatchlistItemResponse[];
  marketDataStatusByConid: Record<string, { label: string; help: string }>;
  forecastsByConid: Record<string, ForecastByAccountRow>;
};

function VolglijstConfirmedView() {
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState<IbkrContractCandidate[]>([]);
  const [selected, setSelected] = useState<IbkrContractCandidate | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ibkrWatchlists, setIbkrWatchlists] = useState<IbkrWatchlistSummary[]>(
    [],
  );
  const [selectedWatchlist, setSelectedWatchlist] = useState<string>("");
  const [watchlistInstruments, setWatchlistInstruments] = useState<
    IbkrWatchlistInstrument[]
  >([]);
  const [ibkrStatus, setIbkrStatus] = useState<string>("");
  const [openForecastConid, setOpenForecastConid] = useState<string | null>(
    null,
  );

  const watchlistQuery = useQuery({
    queryKey: ["volglijst-confirmed-view"],
    queryFn: async (): Promise<WatchlistViewData> => {
      const res = await listWatchlistItems();
      if (!res.ok) throw new Error("unreachable");
      const entries = await Promise.all(
        res.data.items
          .map((wrapped) => wrapped.item.ibkr_conid)
          .filter((conid): conid is string => Boolean(conid && conid.trim()))
          .map(async (conid) => {
            const status = await getMarketDataLatestSnapshotStatus(conid);
            if (!status.ok) {
              return [
                conid,
                {
                  label: "Providerfout",
                  help: "Status kon niet worden opgehaald.",
                },
              ] as const;
            }
            if (status.data.status === "snapshot_available") {
              return [
                conid,
                {
                  label: status.data.status_nl,
                  help: `${status.data.price_basis_nl ?? "Alleen opgeslagen snapshot"}. ${status.data.valuation_readiness_status ?? "ready_for_status_only"}`,
                },
              ] as const;
            }
            if (status.data.status === "missing_snapshot") {
              return [
                conid,
                {
                  label: "Geen marktdata",
                  help: "Waardering nog niet beschikbaar.",
                },
              ] as const;
            }
            if (status.data.status === "not_configured") {
              return [
                conid,
                {
                  label: "Niet geconfigureerd",
                  help: status.data.next_step_nl,
                },
              ] as const;
            }
            return [
              conid,
              { label: "Alleen status", help: status.data.next_step_nl },
            ] as const;
          }),
      );
      const forecastResult = await apiClient.getForecastsByAccount();
      return {
        items: res.data.items,
        marketDataStatusByConid: Object.fromEntries(entries),
        forecastsByConid: forecastResult.ok
          ? Object.fromEntries(
              forecastResult.data.items.map((row) => [row.conid, row]),
            )
          : {},
      };
    },
  });
  const items = watchlistQuery.data?.items ?? [];
  const marketDataStatusByConid =
    watchlistQuery.data?.marketDataStatusByConid ?? {};
  const forecastsByConid = watchlistQuery.data?.forecastsByConid ?? {};
  const reload = () => watchlistQuery.refetch();
  const getReadinessStatus = (wrapped: WatchlistItemResponse) =>
    wrapped.asset_listing_readiness.status_nl;
  const getReadinessHelp = (wrapped: WatchlistItemResponse) =>
    wrapped.asset_listing_readiness.next_step_nl;

  return (
    <main className="page-wrap">
      <h2>Volglijst</h2>

      <div
        data-testid="volglijst-suggesties-link-banner"
        style={{
          background: "#e0f2fe",
          color: "#075985",
          padding: "8px 12px",
          borderRadius: 6,
          marginBottom: 12,
          fontSize: 13,
        }}
      >
        Volglijst is je tracking-overzicht: hier zie je welke assets je
        volgt en de laatste voorspellings-band. Voor concrete actie-
        suggesties (Kopen / Verkopen / ...){" "}
        <Link
          href="/suggesties"
          data-testid="volglijst-suggesties-link"
          style={{ color: "#0369a1", textDecoration: "underline" }}
        >
          ga naar /suggesties
        </Link>
        .
      </div>

      <h3>Importeren uit IBKR-watchlist</h3>
      <p>Eerst kandidaten ophalen. Geen automatische verwijdering.</p>
      <button
        type="button"
        onClick={async () => {
          const r = await listIbkrWatchlists();
          if (!r.ok) {
            setIbkrStatus("Niet geconfigureerd");
            return;
          }
          setIbkrStatus(r.data.message_nl);
          setIbkrWatchlists(r.data.items);
        }}
      >
        IBKR-watchlists ophalen
      </button>
      <p>{ibkrStatus || "Niet geconfigureerd"}</p>
      <ul>
        {ibkrWatchlists.map((wl) => (
          <li key={wl.ibkr_watchlist_id}>
            <button
              type="button"
              onClick={async () => {
                setSelectedWatchlist(wl.ibkr_watchlist_id);
                const r = await listIbkrWatchlistInstruments(
                  wl.ibkr_watchlist_id,
                );
                if (!r.ok) return;
                setWatchlistInstruments(r.data.items);
              }}
            >
              {wl.name} ({wl.ibkr_watchlist_id}) - Instrumenten bekijken
            </button>
          </li>
        ))}
      </ul>
      {selectedWatchlist ? (
        <button
          type="button"
          onClick={async () => {
            const r = await importIbkrWatchlist(selectedWatchlist);
            if (!r.ok) {
              setError("Import mislukt.");
              return;
            }
            setWatchlistInstruments(r.data.candidates);
          }}
        >
          Import voorbereiden
        </button>
      ) : null}
      <ul>
        {watchlistInstruments.map((i, ix) => (
          <li key={`${i.ibkr_conid ?? "none"}-${ix}`}>
            {i.symbol ?? "Onbekend"} - {i.ibkr_conid ?? "Geen conid"} -{" "}
            {i.import_status === "already_in_local_watchlist"
              ? "Al aanwezig"
              : i.import_status === "needs_review"
                ? "Controle nodig"
                : i.import_status === "candidate"
                  ? "Kandidaat"
                  : "Overgeslagen"}
          </li>
        ))}
      </ul>

      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const r = await searchIbkrContracts(query);
          if (!r.ok) {
            setError("Zoeken mislukt.");
            return;
          }
          setCandidates(r.data.items ?? []);
          setSelected(null);
        }}
      >
        <label>
          Zoek IBKR-instrument{" "}
          <input value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <button type="submit">Zoeken</button>
      </form>
      <p>Kies het juiste instrument</p>
      {candidates.map((c) => (
        <button
          key={c.candidate_id}
          type="button"
          onClick={() => setSelected(c)}
        >
          {c.symbol} - {c.company_name ?? "Niet beschikbaar"} -{" "}
          {c.asset_class ?? "Type onbekend"} - Beurs:{" "}
          {c.exchange ?? "Niet beschikbaar"} - Valuta:{" "}
          {c.currency ?? "Niet beschikbaar"} - IBKR-contract: {c.ibkr_conid}
        </button>
      ))}
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (!selected) {
            setError("Kies eerst een instrument.");
            return;
          }
          const r = await createWatchlistItem({
            ibkr_conid: selected.ibkr_conid,
            ibkr_symbol: selected.symbol,
            ibkr_contract_name: selected.company_name,
            ibkr_security_type: selected.asset_class,
            ibkr_exchange: selected.exchange,
            ibkr_primary_exchange: selected.primary_exchange,
            ibkr_currency: selected.currency,
            ibkr_validation_status: "valid",
            note: note || null,
          });
          if (!r.ok) {
            setError("Toevoegen mislukt.");
            return;
          }
          setNote("");
          setQuery("");
          setCandidates([]);
          setSelected(null);
          await reload();
        }}
      >
        <label>
          Notitie{" "}
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <button type="submit">Toevoegen aan Volglijst</button>
      </form>
      {error ? <p>{error}</p> : null}

      <table>
        <thead>
          <tr>
            <th>Symbool</th>
            <th>IBKR-contract</th>
            <th>Gevalideerd</th>
            <th>Status</th>
            <th>Marktdata</th>
            <th>Voorspelling-band</th>
            <th>Actie</th>
          </tr>
        </thead>
        <tbody>
          {items.map((wrapped) => {
            const i = wrapped.item;
            const marketStatus = i.ibkr_conid
              ? marketDataStatusByConid[i.ibkr_conid]
              : null;
            const forecast = i.ibkr_conid
              ? forecastsByConid[i.ibkr_conid]
              : null;
            return (
              <tr
                key={i.watchlist_item_id}
                data-testid={`volglijst-row-${i.symbol}`}
              >
                <td>{i.symbol}</td>
                <td>{i.ibkr_conid ?? "Geen contract"}</td>
                <td>{wrapped.ibkr_status_label_nl}</td>
                <td>
                  <strong>{getReadinessStatus(wrapped)}</strong>
                  <br />
                  <small>{getReadinessHelp(wrapped)}</small>
                </td>
                <td>
                  {i.ibkr_conid ? (
                    <>
                      <StatusBadge
                        label={marketStatus?.label ?? "Alleen status"}
                        status="info"
                        title={marketStatus?.help ?? "Nog geen analyse"}
                      />
                      <br />
                      <small>{marketStatus?.help ?? "Nog geen analyse"}</small>
                    </>
                  ) : (
                    <>
                      <StatusBadge
                        label="Geen contract"
                        status="geblokkeerd"
                        title="Contract niet aanwezig of niet gevalideerd."
                      />
                      <br />
                      <small>Contract niet gevalideerd</small>
                    </>
                  )}
                </td>
                <td data-testid={`volglijst-forecast-cell-${i.symbol}`}>
                  {forecast ? (
                    <>
                      <small
                        data-testid={`volglijst-forecast-interval-${i.symbol}`}
                      >
                        p10 {forecast.p10_log_return} / p50{" "}
                        {forecast.p50_log_return} / p90{" "}
                        {forecast.p90_log_return} • kans op stijging{" "}
                        {forecast.prob_positive} • horizon{" "}
                        {forecast.horizon_trading_days} dagen
                      </small>
                      <br />
                      <small>Betrouwbaarheid: {forecast.confidence_level}</small>
                      <br />
                      <button
                        type="button"
                        data-testid={`volglijst-forecast-why-${i.symbol}`}
                        onClick={() => setOpenForecastConid(i.ibkr_conid)}
                      >
                        Waarom?
                      </button>
                    </>
                  ) : (
                    <small title="Geen voorspelling beschikbaar — wacht op morgenrun of forecast is geblokkeerd.">
                      —
                    </small>
                  )}
                </td>
                <td>
                  <button
                    onClick={async () => {
                      await archiveWatchlistItem(i.watchlist_item_id);
                      await reload();
                    }}
                  >
                    Archiveren
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {openForecastConid ? (
        <ForecastExplanationPanel
          conid={openForecastConid}
          open={true}
          onClose={() => setOpenForecastConid(null)}
        />
      ) : null}
    </main>
  );
}
