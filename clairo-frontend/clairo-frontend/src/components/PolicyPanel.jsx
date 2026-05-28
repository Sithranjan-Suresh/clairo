import { useState } from "react";
import { retrievePolicy } from "../api";
import { Spinner, ErrorBox, SectionHeader } from "./ui";

export default function PolicyPanel({ uploadResult }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  const canRetrieve =
    uploadResult?.structured_claim?.payer &&
    uploadResult?.structured_claim?.cpt_codes;

  async function handleRetrieve() {
    setError(null);
    setLoading(true);
    setResults(null);
    try {
      const claim = uploadResult.structured_claim;
      const cptCodes = claim.cpt_codes;
      const cpt = Array.isArray(cptCodes) ? cptCodes[0] : cptCodes ?? "";
      const data = await retrievePolicy(
        claim.payer ?? "",
        cpt,
        claim.denial_reason ?? "",
        uploadResult.classification ?? ""
      );
      setResults(data.results ?? []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <SectionHeader
        icon="📚"
        title="Policy Citation Retrieval"
        subtitle="Payer policy excerpts that govern this denial"
      />

      {!canRetrieve && (
        <p className="hint">Upload a denial document first to retrieve policy citations.</p>
      )}

      {canRetrieve && (
        <button
          className="btn-primary"
          onClick={handleRetrieve}
          disabled={loading}
        >
          {loading ? <><Spinner size={16} /> Retrieving Policies…</> : "Retrieve Policy Citations"}
        </button>
      )}

      <ErrorBox message={error} />

      {results !== null && results.length === 0 && (
        <p className="hint">No matching policy sections found for this payer/procedure combination.</p>
      )}

      {results && results.length > 0 && (
        <div className="policy-list">
          {results.map((r, i) => (
            <div key={i} className="policy-card">
              <div className="policy-card-header">
                <span className="policy-badge">Chunk {r.chunk_index ?? i + 1}</span>
                <span className="policy-source">{r.source ?? "Unknown Source"}</span>
              </div>
              {r.score != null && (
                <div className="field-row" style={{ marginBottom: "8px" }}>
                  <span className="field-label">Relevance Score</span>
                  <span className="field-value">{(r.score * 100).toFixed(1)}%</span>
                </div>
              )}
              <div className="policy-text">{r.text ?? "No content available."}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
