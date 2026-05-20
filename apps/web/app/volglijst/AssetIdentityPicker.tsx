"use client";

import { useEffect, useState } from "react";

import { searchAssetMasterIdentities, type AssetMasterSearchRecord } from "@/lib/apiClient";

type Props = {
  selectedAsset: AssetMasterSearchRecord | null;
  onSelect: (asset: AssetMasterSearchRecord) => void;
  onClear: () => void;
};

export function AssetIdentityPicker({ selectedAsset, onSelect, onClear }: Props) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<AssetMasterSearchRecord[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      const res = await searchAssetMasterIdentities(query);
      if (cancelled) {
        return;
      }
      if (!res.ok) {
        setError("Asset-identiteiten laden mislukt.");
        setResults([]);
      } else {
        setResults(res.data.records);
      }
      setLoading(false);
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [query]);

  return (
    <section>
      <label>
        Asset-identiteit zoeken
        <input
          placeholder="Zoek asset-identiteit…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <p title="Asset-identiteit helpt het systeem later data en bewijs correct te koppelen.">
        Asset-identiteit helpt het systeem later data en bewijs correct te koppelen.
      </p>
      {loading ? <p>Bezig met zoeken…</p> : null}
      {error ? <p>{error}</p> : null}
      {!loading && !error && results.length === 0 ? (
        <p>Geen bestaande asset-identiteit gevonden.</p>
      ) : null}
      <ul>
        {results.map((asset) => (
          <li key={asset.asset_id}>
            <button type="button" onClick={() => onSelect(asset)}>
              {asset.canonical_symbol} — {asset.asset_name} ({asset.primary_exchange ?? "Onbekend"}/
              {asset.primary_currency ?? "Onbekend"})
            </button>
            <span>
              Type: {asset.asset_type} | Status: {asset.status}
            </span>
          </li>
        ))}
      </ul>
      {selectedAsset ? (
        <div>
          <p>
            Geselecteerd: {selectedAsset.canonical_symbol} — {selectedAsset.asset_name} ({selectedAsset.asset_id})
          </p>
          <p>
            Beurs/valuta: {selectedAsset.primary_exchange ?? "Onbekend"}/{selectedAsset.primary_currency ?? "Onbekend"} | Type: {selectedAsset.asset_type}
          </p>
          <p>Identifiers: {selectedAsset.identifier_summary_nl}</p>
          <button type="button" onClick={onClear}>
            Selectie wissen
          </button>
        </div>
      ) : null}
    </section>
  );
}
