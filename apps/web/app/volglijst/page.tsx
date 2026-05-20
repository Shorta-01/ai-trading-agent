"use client";

import { useEffect, useState } from "react";
import {
  archiveWatchlistItem,
  createWatchlistItem,
  listWatchlistItems,
  searchIbkrContracts,
  type IbkrContractCandidate,
  type WatchlistItemResponse,
} from "@/lib/apiClient";

export default function Page() {
  const [items, setItems] = useState<WatchlistItemResponse[]>([]);
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState<IbkrContractCandidate[]>([]);
  const [selected, setSelected] = useState<IbkrContractCandidate | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() { const res = await listWatchlistItems(); if (res.ok) setItems(res.data.items); }
  useEffect(() => { void load(); }, []);

  return <main className="page-wrap"><h2>Volglijst</h2><p>Geen actief Volglijst-item zonder IBKR-contract.</p>
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
    <table><thead><tr><th>Symbool</th><th>IBKR-contract</th><th>Gevalideerd</th><th>Status</th><th>Actie</th></tr></thead><tbody>{items.map((wrapped)=>{const i=wrapped.item; return <tr key={i.watchlist_item_id}><td>{i.symbol}</td><td>{i.ibkr_conid ?? "Niet beschikbaar"}</td><td>{wrapped.ibkr_status_label_nl}</td><td>{wrapped.analysis_readiness_label_nl}</td><td><button onClick={async()=>{await archiveWatchlistItem(i.watchlist_item_id); await load();}}>Archiveren</button></td></tr>;})}</tbody></table>
  </main>;
}
