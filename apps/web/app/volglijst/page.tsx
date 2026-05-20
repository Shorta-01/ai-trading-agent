"use client";

import { useEffect, useState } from "react";
import { archiveWatchlistItem, createWatchlistItem, listWatchlistItems, type WatchlistItem } from "@/lib/apiClient";

export default function Page() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [symbol, setSymbol] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const res = await listWatchlistItems();
    if (!res.ok) {
      setError("Volglijst kon niet worden geladen.");
      return;
    }
    setItems(res.data.items);
  }
  useEffect(() => { void load(); }, []);

  return <main className="page-wrap"><h2>Volglijst</h2><p>Lokale volgassets voor onderzoek. Dit zijn geen IBKR-posities.</p>
    <form onSubmit={async (e)=>{e.preventDefault(); setError(null); const r=await createWatchlistItem({symbol,note: note || null}); if(!r.ok){setError("Toevoegen mislukt.");return;} setSymbol(""); setNote(""); await load();}}>
      <label>Symbool <input value={symbol} onChange={(e)=>setSymbol(e.target.value)} /></label>
      <label>Notitie <input value={note} onChange={(e)=>setNote(e.target.value)} /></label>
      <button type="submit">Toevoegen</button>
    </form>
    {error ? <p>{error}</p> : null}
    {items.length===0 ? <p>Nog geen volglijst-items. Voeg handmatig een asset toe.</p> : <table><thead><tr><th>Symbool</th><th>Naam</th><th>Beurs</th><th>Valuta</th><th>Type</th><th>Status</th><th>Notitie</th><th>Laatst aangepast</th><th>Actie</th></tr></thead><tbody>{items.map((i)=><tr key={i.watchlist_item_id}><td>{i.symbol}</td><td>{i.name ?? "Niet beschikbaar"}</td><td>{i.exchange ?? "Niet beschikbaar"}</td><td>{i.currency ?? "Niet beschikbaar"}</td><td>{i.security_type ?? "Niet beschikbaar"}</td><td>{i.status}</td><td>{i.note ?? "Niet beschikbaar"}</td><td>{new Date(i.updated_at).toLocaleString("nl-BE")}</td><td><button onClick={async()=>{await archiveWatchlistItem(i.watchlist_item_id); await load();}}>Archiveren</button></td></tr>)}</tbody></table>}
  </main>;
}
