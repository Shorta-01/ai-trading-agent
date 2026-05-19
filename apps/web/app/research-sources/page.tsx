"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { SectionHeader } from "@/components/SectionHeader";
import { apiClient, ResearchSourceRecord } from "@/lib/apiClient";

const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md", ".csv", ".docx", ".xlsx", ".pptx"];

type UploadResult = {
  library_source_id: string;
  status: string;
  original_filename: string;
  stored_filename: string;
  file_size_bytes: number;
  sha256_hash: string;
  explanation_nl: string;
  archive_storage_uri?: string | null;
};

function f(value?: string | null) {
  return value && value.trim() !== "" ? value : "Niet ingevuld";
}

export default function ResearchSourcesPage() {
  const [sources, setSources] = useState<ResearchSourceRecord[]>([]);
  const [selected, setSelected] = useState<ResearchSourceRecord | null>(null);
  const [status, setStatus] = useState("Laden...");
  const [error, setError] = useState("");
  const [urlMeta, setUrlMeta] = useState<Record<string, unknown> | null>(null);
  const [note, setNote] = useState<Record<string, unknown> | null>(null);
  const [processing, setProcessing] = useState<Record<string, unknown> | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState("");
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const selectedSourceId = useMemo(() => selected?.library_source_id ?? "", [selected]);

  async function loadSources() {
    const response = await apiClient.listResearchSources();
    if (!response.ok) {
      if (response.status === 503) {
        setError("De opslag is nog niet verbonden. De onderzoeksbibliotheek kan de bron nog niet bewaren.");
      } else {
        setError("Onderzoeksbronnen konden niet geladen worden.");
      }
      setStatus("Onderzoeksbibliotheek: niet beschikbaar");
      return;
    }
    setSources(response.data.records);
    setStatus("Onderzoeksbibliotheek: beschikbaar");
    setError("");
  }

  useEffect(() => {
    void loadSources();
  }, []);

  async function onCreateSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      library_source_id: form.get("library_source_id"), title: form.get("title"), source_kind: form.get("source_kind"), document_type: form.get("document_type"), source_type: form.get("source_kind"),
      asset_symbol: form.get("asset_symbol") || null, asset_name: form.get("asset_name") || null, explanation_nl: form.get("explanation_nl"),
      status: "active", classification_status: "pending", extraction_status: "pending", analysis_status: "pending", raw_source_available: false, schema_version: "v1",
    };
    const response = await apiClient.createResearchSource(payload);
    setError(response.ok ? "Onderzoeksbron opgeslagen als metadata." : "Bronmetadata kon niet worden opgeslagen.");
    await loadSources();
  }

  async function loadSelectedDetails(source: ResearchSourceRecord) {
    setSelected(source);
    const [urlResponse, noteResponse, processingResponse] = await Promise.all([
      apiClient.getUrlMetadata(source.library_source_id), apiClient.getUserNote(source.library_source_id), apiClient.getLatestProcessingStatus(source.library_source_id),
    ]);
    setUrlMeta(urlResponse.ok ? urlResponse.data.record : null);
    setNote(noteResponse.ok ? noteResponse.data.record : null);
    setProcessing(processingResponse.ok ? processingResponse.data.record : null);
  }

  async function onUploadFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUploadError("");
    setUploadSuccess("");
    setUploadResult(null);

    const form = new FormData(event.currentTarget);
    const librarySourceId = String(form.get("upload_library_source_id") ?? "").trim();
    const fileInput = form.get("file");

    if (!librarySourceId) {
      setUploadError("Bron-ID is verplicht.");
      return;
    }
    if (!(fileInput instanceof File) || fileInput.size === 0) {
      setUploadError("Kies eerst een bestand om te uploaden.");
      return;
    }

    const filename = fileInput.name;
    if (filename.includes("/") || filename.includes("\\") || filename.includes("..")) {
      setUploadError("De bestandsnaam is onveilig. Kies een veilige bestandsnaam zonder mappen of punt-punt.");
      return;
    }
    const lowerName = filename.toLowerCase();
    const isAllowed = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
    if (!isAllowed) {
      setUploadError("Dit bestandstype is niet toegestaan voor onderzoeksbronnen.");
      return;
    }

    const response = await apiClient.uploadResearchSourceFile(librarySourceId, fileInput, {
      title: String(form.get("upload_title") ?? "").trim() || undefined,
      assetSymbol: String(form.get("upload_asset_symbol") ?? "").trim() || undefined,
      assetName: String(form.get("upload_asset_name") ?? "").trim() || undefined,
      documentType: String(form.get("upload_document_type") ?? "").trim() || undefined,
      sourceKind: "file_upload",
      sourceType: "document",
      explanationNl: String(form.get("upload_explanation_nl") ?? "").trim() || undefined,
    });

    if (!response.ok) {
      if (response.status === 400) {
        setUploadError("Het bestand werd geweigerd. Controleer de bestandsnaam en het bestandstype.");
      } else if (response.status === 413) {
        setUploadError("Het bestand is te groot volgens de huidige uploadlimiet.");
      } else if (response.status === 503) {
        setUploadError("De opslag is nog niet verbonden. Het bestand kan niet worden opgeslagen.");
      } else if (response.status === 409 || response.message.toLowerCase().includes("disabled")) {
        setUploadError("Bestand uploaden staat momenteel uit.");
      } else {
        setUploadError("Upload mislukt. Probeer opnieuw of controleer de instellingen.");
      }
      return;
    }

    setUploadSuccess("Bestand veilig opgeslagen als onderzoeksbron. Het bestand is nog niet gelezen, geparseerd of geanalyseerd.");
    setUploadResult(response.data);

    await loadSources();
    const updated = await apiClient.getResearchSource(librarySourceId);
    if (updated.ok) {
      await loadSelectedDetails(updated.data.record);
    }
  }

  return (
    <main className="container">
      <h1>Onderzoeksbibliotheek</h1>
      <p>Hier bewaar je bronnen die later kunnen helpen bij het onderzoek naar assets. Denk aan URL’s, notities, jaarverslagen, kwartaalrapporten of factsheets. In deze versie bewaart het systeem alleen metadata. Er worden nog geen bestanden gelezen, URL’s opgehaald of AI-analyses gestart.</p>

      <section className="dashboard-card">
        <SectionHeader title="Status" helpText="Deze status toont of metadata-opslag bereikbaar is." />
        <p>{status}</p><p>Opslagstatus: {error ? "Niet beschikbaar" : "Beschikbaar"}</p>{error ? <p>Laatste fout: {error}</p> : null}
        <p className="help-text">Help: Bij een opslagfout zie je alleen een veilige melding in eenvoudige taal.</p>
      </section>

      <section>
        <SectionHeader title="Bronmetadata toevoegen" helpText="Sla alleen metadata op; geen upload, parsing of analyse." />
        <form onSubmit={onCreateSource} className="grid one-column">
          <label>Bron-ID<input name="library_source_id" required /><span className="help-text">Unieke naam of code voor deze bron.</span></label>
          <label>Titel<input name="title" required /><span className="help-text">Korte duidelijke naam voor deze bron.</span></label>
          <label>Soort bron<input name="source_kind" required /><span className="help-text">Waar komt deze bron vandaan, bijvoorbeeld URL, notitie of documentmetadata.</span></label>
          <label>Documenttype<input name="document_type" required /><span className="help-text">Wat voor bron is dit, bijvoorbeeld jaarverslag, kwartaalrapport, factsheet, URL of notitie.</span></label>
          <label>Asset symbool<input name="asset_symbol" /><span className="help-text">Optioneel. Vul dit in als de bron bij een bepaald aandeel, ETF of fonds hoort.</span></label>
          <label>Asset naam<input name="asset_name" /><span className="help-text">Optioneel. Naam van het asset als die bekend is.</span></label>
          <label>Uitleg<textarea name="explanation_nl" required /><span className="help-text">Leg kort uit waarom je deze bron toevoegt.</span></label>
          <button type="submit">Bronmetadata bewaren</button>
        </form>
      </section>

      <section className="dashboard-card">
        <SectionHeader title="Bestand uploaden" helpText="Bestanden worden veilig bewaard als onderzoeksbron. Er wordt nog geen analyse uitgevoerd." />
        <form className="grid one-column" onSubmit={onUploadFile}>
          <label>Bron-ID<input name="upload_library_source_id" defaultValue={selectedSourceId} required /><span className="help-text">Kies de Bron-ID waar dit bestand bij hoort.</span></label>
          <label>Bestand<input name="file" type="file" accept={ALLOWED_EXTENSIONS.join(",")} required /><span className="help-text">Selecteer een toegestaan bestandstype.</span></label>
          <label>Titel<input name="upload_title" /><span className="help-text">Optioneel. Duidelijke titel van het bestand.</span></label>
          <label>Asset symbool<input name="upload_asset_symbol" /><span className="help-text">Optioneel. Symbool van het bijbehorende asset.</span></label>
          <label>Asset naam<input name="upload_asset_name" /><span className="help-text">Optioneel. Naam van het bijbehorende asset.</span></label>
          <label>Documenttype<input name="upload_document_type" /><span className="help-text">Optioneel. Bijvoorbeeld jaarverslag of factsheet.</span></label>
          <label>Uitleg<textarea name="upload_explanation_nl" /><span className="help-text">Optioneel. Leg uit waarom dit bestand relevant is.</span></label>
          <button type="submit">Bestand veilig uploaden</button>
        </form>
        <p className="help-text">Het bestand wordt alleen veilig bewaard met metadata en SHA-256 hash. Het systeem gebruikt dit bestand nog niet voor suggesties.</p>
        <ul>
          <li>Toegelaten bestandstypes: PDF, TXT, Markdown, CSV, DOCX, XLSX en PPTX.</li>
          <li>Bestanden worden veilig opgeslagen, maar nog niet gelezen of geanalyseerd.</li>
          <li>Een upload maakt geen koop- of verkoopactie aan.</li>
          <li>Een upload maakt geen IBKR-actie aan.</li>
          <li>Een upload maakt geen automatische suggestie aan.</li>
          <li>Een upload wordt eerst geblokkeerd voor suggesties tot latere controles klaar zijn.</li>
          <li>Maximale bestandsgrootte hangt af van de API-instelling. Grote bestanden kunnen geweigerd worden.</li>
        </ul>
        {uploadError ? <p>{uploadError}</p> : null}
        {uploadSuccess ? <p>{uploadSuccess}</p> : null}
        {uploadResult ? <div className="dashboard-card upload-result-block">
          <p>Status: Geblokkeerd voor suggesties</p>
          <p>Bestandsnaam: {uploadResult.original_filename}</p>
          <p>Opgeslagen naam: {uploadResult.stored_filename}</p>
          <p>Bestandsgrootte: {uploadResult.file_size_bytes} bytes</p>
          <p>SHA-256 hash: <span className="hash-text">{uploadResult.sha256_hash}</span></p>
          <p>Bron-ID: {uploadResult.library_source_id}</p>
          <p>Uitleg: {f(uploadResult.explanation_nl)}</p>
          <p>Nog geen analyse uitgevoerd</p>
          {uploadResult.archive_storage_uri ? <p>Interne archiefreferentie: {uploadResult.archive_storage_uri}</p> : null}
          <p className="help-text">De SHA-256 hash is een technische vingerafdruk van het bestand. Zo kan het systeem later controleren of hetzelfde bestand opnieuw werd gebruikt of gewijzigd.</p>
        </div> : null}
      </section>

      <section>
        <SectionHeader title="Onderzoeksbronnen" helpText="Lijst met opgeslagen metadatarecords." />
        {sources.length === 0 ? <p>Nog geen onderzoeksbronnen toegevoegd.</p> : (
          <table><thead><tr><th>Titel</th><th>Asset</th><th>Soort bron</th><th>Documenttype</th><th>Status</th><th>Analyse</th><th>Actie</th></tr></thead><tbody>
            {sources.map((source) => <tr key={source.library_source_id}><td>{source.title}</td><td>{source.asset_symbol ?? "-"}</td><td>{source.source_kind}</td><td>{source.document_type}</td><td>{source.status}</td><td>{source.analysis_status}</td><td><button type="button" onClick={() => void loadSelectedDetails(source)}>Bekijken</button></td></tr>)}
          </tbody></table>
        )}
      </section>

      {selected ? <section className="dashboard-card"><SectionHeader title="Brondetails" helpText="Deze bron is bewijs en geen handelsinstructie." />
        <p>Bron-ID: {selected.library_source_id}</p><p>Titel: {selected.title}</p><p>Asset symbool: {f(selected.asset_symbol)}</p><p>Asset naam: {f(selected.asset_name)}</p><p>Soort bron: {selected.source_kind}</p><p>Documenttype: {selected.document_type}</p><p>Bronkwaliteit: {f(selected.source_credibility_level)}</p><p>Prompt-injectierisico: {f(selected.prompt_injection_risk_level)}</p><p>Aangemaakt op: {selected.created_at}</p><p>Laatst aangepast: {selected.updated_at}</p><p>Uitleg: {selected.explanation_nl}</p>
        <p><strong>Deze bron is bewijs voor later onderzoek. Ze is geen handelsinstructie en maakt geen koop- of verkoopactie aan.</strong></p>
      </section> : null}

      {selected ? <section>
        <SectionHeader title="URL-metadata" helpText="De URL wordt niet opgehaald of geanalyseerd in deze versie." />
        <form className="grid one-column" onSubmit={async (e) => { e.preventDefault(); const form = new FormData(e.currentTarget); const res = await apiClient.createUrlMetadata(selected.library_source_id, { url: form.get("url"), normalized_url: form.get("normalized_url") || null, domain: form.get("domain") || null, content_type: form.get("content_type") || null, explanation_nl: form.get("explanation_nl") }); setError(res.ok ? "URL-metadata opgeslagen. De URL wordt nog niet opgehaald of geanalyseerd." : "URL-metadata kon niet worden opgeslagen."); await loadSelectedDetails(selected); }}>
          <label>URL<input name="url" required /></label><label>Genormaliseerde URL<input name="normalized_url" /></label><label>Domein<input name="domain" /></label><label>Contenttype<input name="content_type" /></label><label>Uitleg<textarea name="explanation_nl" required /></label><button type="submit">URL-metadata bewaren</button>
        </form>
        {urlMeta ? <p>Laatste URL: {String(urlMeta.url ?? "")}</p> : <p>Nog geen URL-metadata beschikbaar.</p>}
      </section> : null}

      {selected ? <section>
        <SectionHeader title="Gebruikersnotitie" helpText="Notities zijn bewijs, geen handelsinstructie." />
        <form className="grid one-column" onSubmit={async (e) => { e.preventDefault(); const form = new FormData(e.currentTarget); const res = await apiClient.createUserNote(selected.library_source_id, { title: form.get("title"), note_nl: form.get("note_nl"), thesis_relevance_nl: form.get("thesis_relevance_nl") || null, user_confidence_nl: form.get("user_confidence_nl") || null, explanation_nl: form.get("explanation_nl"), asset_symbol: selected.asset_symbol }); setError(res.ok ? "Gebruikersnotitie opgeslagen als onderzoeksbron. Dit is bewijs, geen handelsinstructie." : "Notitie kon niet worden opgeslagen."); await loadSelectedDetails(selected); }}>
          <label>Titel<input name="title" required /></label><label>Notitie<textarea name="note_nl" required /></label><label>Relevantie voor thesis<input name="thesis_relevance_nl" /></label><label>Gebruikerszekerheid<input name="user_confidence_nl" /></label><label>Uitleg<textarea name="explanation_nl" required /></label><button type="submit">Notitie bewaren</button>
        </form>
        {note ? <p>Laatste notitie: {String(note.title ?? "")}</p> : <p>Nog geen notitie beschikbaar.</p>}
      </section> : null}

      {selected ? <section className="dashboard-card"><SectionHeader title="Verwerkingsstatus" helpText="Deze status toont alleen of de bron later gebruikt mag worden. Er wordt in deze versie nog geen automatische analyse gestart." />
        {processing ? <><p>Classificatie: {String(processing.classification_status ?? "-")}</p><p>Extractie: {String(processing.extraction_status ?? "-")}</p><p>Analyse: {String(processing.analysis_status ?? "-")}</p><p>Klaar voor onderzoek: {processing.can_be_used_in_research ? "Ja" : "Nee"}</p><p>Klaar voor suggesties: {processing.can_be_used_in_suggestions ? "Ja" : "Nee"}</p><p>Gebruikerscontrole nodig: {processing.needs_user_review ? "Ja" : "Nee"}</p><p>Blokkeert suggesties: {processing.blocks_suggestions ? "Ja" : "Nee"}</p><p>Reden: {String(processing.reason_nl ?? "-")}</p><p className="help-text">Dit bestand is bewaard, maar nog niet gecontroleerd of geanalyseerd. Daarom mag het nog geen invloed hebben op suggesties.</p></> : <p>Nog geen verwerkingsstatus beschikbaar.</p>}
      </section> : null}

      <section className="dashboard-card">
        <h2>Veiligheid en hulp</h2>
        <p>De onderzoeksbibliotheek bewaart bronnen voor later onderzoek. Een bron kan later helpen om een asset beter te begrijpen, maar een bron is nooit rechtstreeks een koop- of verkoopopdracht. Het systeem moet bronnen eerst controleren op kwaliteit, actualiteit en prompt-injectierisico voordat ze invloed mogen hebben op een suggestie.</p>
        <ul><li>Bestandupload is beschikbaar als veilige opslag</li><li>Geen URL-ophaling in deze versie</li><li>Geen AI-analyse in deze versie</li><li>Geen IBKR-actie in deze versie</li><li>Geen automatische suggestie in deze versie</li></ul>
      </section>
    </main>
  );
}
