"use client";

import { useEffect, useState } from "react";
import {
  archiveWatchlistItem,
  createWatchlistItem,
  listWatchlistItems,
  updateWatchlistItem,
  type AssetMasterSearchRecord,
  type WatchlistItemResponse,
} from "@/lib/apiClient";
import { AssetIdentityPicker } from "./AssetIdentityPicker";

export default function Page() {
  const [items, setItems] = useState<WatchlistItemResponse[]>([]);
  const [symbol, setSymbol] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [selectedByItem, setSelectedByItem] = useState<Record<string, AssetMasterSearchRecord | null>>({});

  async function load() {
    const res = await listWatchlistItems();
    if (!res.ok) {
      setError("Volglijst kon niet worden geladen.");
      return;
    }
    setItems(res.data.items);
  }
  useEffect(() => {
    void load();
  }, []);

  return <main className="page-wrap"><h2>Volglijst</h2><p>Lokale volgassets voor onderzoek. Dit zijn geen IBKR-posities.</p>
    <form onSubmit={async (e)=>{e.preventDefault(); setError(null); const r=await createWatchlistItem({symbol,note: note || null}); if(!r.ok){setError("Toevoegen mislukt.");return;} setSymbol(""); setNote(""); await load();}}>
      <label>Symbool <input value={symbol} onChange={(e)=>setSymbol(e.target.value)} /></label>
      <label>Notitie <input value={note} onChange={(e)=>setNote(e.target.value)} /></label>
      <button type="submit">Toevoegen</button>
    </form>
    {error ? <p>{error}</p> : null}
    {items.length===0 ? <p>Nog geen volglijst-items. Voeg handmatig een asset toe.</p> : <table><thead><tr><th>Symbool</th><th>Naam</th><th>Beurs</th><th>Valuta</th><th>Type</th><th>Status</th><th>Link-status</th><th>Canonieke asset</th><th>Identiteit koppelen</th><th>Notitie</th><th>Laatst aangepast</th><th>Actie</th></tr></thead><tbody>{items.map((wrapped)=>{const i=wrapped.item; const selected=selectedByItem[i.watchlist_item_id] ?? null; return <tr key={i.watchlist_item_id}><td>{i.symbol}</td><td>{i.name ?? "Niet beschikbaar"}</td><td>{i.exchange ?? "Niet beschikbaar"}</td><td>{i.currency ?? "Niet beschikbaar"}</td><td>{i.security_type ?? "Niet beschikbaar"}</td><td>{i.status}</td><td>{wrapped.link_status === "gelinkt" ? "Gelinkt" : "Niet gelinkt"}</td><td>{wrapped.linked_asset ? `${wrapped.linked_asset.asset_name ?? "Niet beschikbaar"} (${wrapped.linked_asset.canonical_symbol ?? "Niet beschikbaar"}) - ${wrapped.linked_asset.primary_exchange ?? "Niet beschikbaar"}/${wrapped.linked_asset.primary_currency ?? "Niet beschikbaar"}` : "Niet beschikbaar"}</td><td><AssetIdentityPicker selectedAsset={selected} onSelect={(asset)=>setSelectedByItem((prev)=>({...prev,[i.watchlist_item_id]:asset}))} onClear={()=>setSelectedByItem((prev)=>({...prev,[i.watchlist_item_id]:null}))} /><button type="button" onClick={async()=>{if(!selected){setError("Selecteer eerst een asset-identiteit."); return;} const r=await updateWatchlistItem(i.watchlist_item_id,{asset_id:selected.asset_id}); if(!r.ok){setError("Koppelen mislukt."); return;} await load();}}>Koppelen</button><button type="button" onClick={async()=>{const r=await updateWatchlistItem(i.watchlist_item_id,{asset_id:null}); if(!r.ok){setError("Ontkoppelen mislukt."); return;} await load();}}>Ontkoppelen</button></td><td>{i.note ?? "Niet beschikbaar"}</td><td>{new Date(i.updated_at).toLocaleString("nl-BE")}</td><td><button onClick={async()=>{await archiveWatchlistItem(i.watchlist_item_id); await load();}}>Archiveren</button></td></tr>;})}</tbody></table>}
  </main>;
}
