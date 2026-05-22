"use client";

import { useEffect, useState } from "react";
import {
  archiveWatchlistItem,
  createWatchlistItem,
  getMarketDataLatestSnapshotStatus,
  importIbkrWatchlist,
  listIbkrWatchlistInstruments,
  listIbkrWatchlists,
  listWatchlistItems,
  searchIbkrContracts,
  type IbkrContractCandidate,
  type IbkrWatchlistInstrument,
  type IbkrWatchlistSummary,
  type WatchlistItemResponse,
} from "@/lib/apiClient";
import { StatusBadge } from "@/components/StatusBadge";

export default function Page() {
  const [items, setItems] = useState<WatchlistItemResponse[]>([]);
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState<IbkrContractCandidate[]>([]);
  const [selected, setSelected] = useState<IbkrContractCandidate | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ibkrWatchlists, setIbkrWatchlists] = useState<IbkrWatchlistSummary[]>([]);
  const [selectedWatchlist, setSelectedWatchlist] = useState<string>("");
  const [watchlistInstruments, setWatchlistInstruments] = useState<IbkrWatchlistInstrument[]>([]);
  const [ibkrStatus, setIbkrStatus] = useState<string>("");
  const [marketDataStatusByConid, setMarketDataStatusByConid] = useState<Record<string, { label: string; help: string }>>({});

  async function load() {
    const res = await listWatchlistItems();
    if (!res.ok) return;
    setItems(res.data.items);
    const entries = await Promise.all(
      res.data.items
        .map((wrapped) => wrapped.item.ibkr_conid)
        .filter((conid): conid is string => Boolean(conid && conid.trim()))
        .map(async (conid) => {
          const status = await getMarketDataLatestSnapshotStatus(conid);
          if (!status.ok) {
            return [conid, { label: "Providerfout", help: "Status kon niet worden opgehaald." }] as const;
          }
          if (status.data.status === "snapshot_available") {
            return [conid, { label: status.data.status_nl, help: `${status.data.price_basis_nl ?? "Alleen opgeslagen snapshot"}. ${status.data.valuation_readiness_status ?? "ready_for_status_only"}` }] as const;
          }
          if (status.data.status === "missing_snapshot") {
            return [conid, { label: "Geen marktdata", help: "Waardering nog niet beschikbaar." }] as const;
          }
          if (status.data.status === "not_configured") {
            return [conid, { label: "Niet geconfigureerd", help: status.data.next_step_nl }] as const;
          }
          return [conid, { label: "Alleen status", help: status.data.next_step_nl }] as const;
        })
    );
    setMarketDataStatusByConid(Object.fromEntries(entries));
  }
  useEffect(() => { void load(); }, []);
  const getReadinessStatus = (wrapped: WatchlistItemResponse) => wrapped.asset_listing_readiness.status_nl;
  const getReadinessHelp = (wrapped: WatchlistItemResponse) => wrapped.asset_listing_readiness.next_step_nl;

  return <main className="page-wrap"><h2>Volglijst</h2><p>Geen actief Volglijst-item zonder IBKR-contract.</p>
    <h3>Importeren uit IBKR-watchlist</h3>
    <p>Eerst kandidaten ophalen. Geen automatische verwijdering.</p>
    <button type="button" onClick={async()=>{const r=await listIbkrWatchlists(); if(!r.ok){setIbkrStatus("Niet geconfigureerd"); return;} setIbkrStatus(r.data.message_nl); setIbkrWatchlists(r.data.items);}}>IBKR-watchlists ophalen</button>
    <p>{ibkrStatus || "Niet geconfigureerd"}</p>
    <ul>{ibkrWatchlists.map((wl)=><li key={wl.ibkr_watchlist_id}><button type="button" onClick={async()=>{setSelectedWatchlist(wl.ibkr_watchlist_id); const r=await listIbkrWatchlistInstruments(wl.ibkr_watchlist_id); if(!r.ok) return; setWatchlistInstruments(r.data.items);}}>{wl.name} ({wl.ibkr_watchlist_id}) - Instrumenten bekijken</button></li>)}</ul>
    {selectedWatchlist ? <button type="button" onClick={async()=>{const r=await importIbkrWatchlist(selectedWatchlist); if(!r.ok){setError("Import mislukt."); return;} setWatchlistInstruments(r.data.candidates);}}>Import voorbereiden</button> : null}
    <ul>{watchlistInstruments.map((i,ix)=><li key={`${i.ibkr_conid ?? 'none'}-${ix}`}>{i.symbol ?? "Onbekend"} - {i.ibkr_conid ?? "Geen conid"} - {i.import_status === "already_in_local_watchlist" ? "Al aanwezig" : i.import_status === "needs_review" ? "Controle nodig" : i.import_status === "candidate" ? "Kandidaat" : "Overgeslagen"}</li>)}</ul>

    <form onSubmit={async (e)=>{e.preventDefault(); const r=await searchIbkrContracts(query); if(!r.ok){setError("Zoeken mislukt."); return;} setCandidates(r.data.items ?? []); setSelected(null);}}>
      <label>Zoek IBKR-instrument <input value={query} onChange={(e)=>setQuery(e.target.value)} /></label>
      <button type="submit">Zoeken</button>
    </form>
    <p>Kies het juiste instrument</p>
    {candidates.map((c)=><button key={c.candidate_id} type="button" onClick={()=>setSelected(c)}>{c.symbol} - {c.company_name ?? "Niet beschikbaar"} - {c.asset_class ?? "Type onbekend"} - Beurs: {c.exchange ?? "Niet beschikbaar"} - Valuta: {c.currency ?? "Niet beschikbaar"} - IBKR-contract: {c.ibkr_conid}</button>)}
    <form onSubmit={async(e)=>{e.preventDefault(); if(!selected){setError("Kies eerst een instrument."); return;} const r=await createWatchlistItem({ibkr_conid:selected.ibkr_conid,ibkr_symbol:selected.symbol,ibkr_contract_name:selected.company_name,ibkr_security_type:selected.asset_class,ibkr_exchange:selected.exchange,ibkr_primary_exchange:selected.primary_exchange,ibkr_currency:selected.currency,ibkr_validation_status:"valid",note:note||null}); if(!r.ok){setError("Toevoegen mislukt."); return;} setNote(""); setQuery(""); setCandidates([]); setSelected(null); await load();}}>
      <label>Notitie <input value={note} onChange={(e)=>setNote(e.target.value)} /></label>
      <button type="submit">Toevoegen aan Volglijst</button>
    </form>
    {error ? <p>{error}</p> : null}
    <table><thead><tr><th>Symbool</th><th>IBKR-contract</th><th>Gevalideerd</th><th>Status</th><th>Marktdata</th><th>Actie</th></tr></thead><tbody>{items.map((wrapped)=>{const i=wrapped.item; const marketStatus = i.ibkr_conid ? marketDataStatusByConid[i.ibkr_conid] : null; return <tr key={i.watchlist_item_id}><td>{i.symbol}</td><td>{i.ibkr_conid ?? "Geen contract"}</td><td>{wrapped.ibkr_status_label_nl}</td><td><strong>{getReadinessStatus(wrapped)}</strong><br /><small>{getReadinessHelp(wrapped)}</small></td><td>{i.ibkr_conid ? <><StatusBadge label={marketStatus?.label ?? "Alleen status"} status="info" title={marketStatus?.help ?? "Nog geen analyse"} /><br /><small>{marketStatus?.help ?? "Nog geen analyse"}</small></> : <><StatusBadge label="Geen contract" status="geblokkeerd" title="Contract niet aanwezig of niet gevalideerd." /><br /><small>Contract niet gevalideerd</small></>}</td><td><button onClick={async()=>{await archiveWatchlistItem(i.watchlist_item_id); await load();}}>Archiveren</button></td></tr>;})}</tbody></table>
  </main>;
}
