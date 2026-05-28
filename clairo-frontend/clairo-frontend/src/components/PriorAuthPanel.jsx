import { useState } from "react";
import { priorAuthCheck } from "../api";

export default function PriorAuthPanel({ uploadResult }) {
  const claim = uploadResult?.structured_claim;

  const [payer, setPayer] = useState(claim?.payer || "");
  const [cptCodes, setCptCodes] = useState((claim?.cpt_codes || []).join(", "));
  const [diagnosisCodes, setDiagnosisCodes] = useState("");
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const res = await priorAuthCheck(
        payer,
        cptCodes.split(",").map(s => s.trim()).filter(Boolean),
        notes,
        diagnosisCodes.split(",").map(s => s.trim()).filter(Boolean)
      );
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <h2>🔐 Prior Authorization Pre-Check</h2>
      <p className="panel-sub">Check if your documentation meets payer PA requirements before submitting.</p>

      <div className="form-group">
        <label>Payer</label>
        <input value={payer} onChange={e => setPayer(e.target.value)} placeholder="e.g. UHC" />
      </div>
      <div className="form-group">
        <label>CPT Codes (comma-separated)</label>
        <input value={cptCodes} onChange={e => setCptCodes(e.target.value)} placeholder="e.g. 29881" />
      </div>
      <div className="form-group">
        <label>Diagnosis Codes (comma-separated, optional)</label>
        <input value={diagnosisCodes} onChange={e => setDiagnosisCodes(e.target.value)} placeholder="e.g. M23.201" />
      </div>
      <div className="form-group">
        <label>Clinical Notes</label>
        <textarea rows={6} value={notes} onChange={e => setNotes(e.target.value)}
          placeholder="Paste clinical notes, progress notes, or relevant documentation here..." />
      </div>

      <button className="btn-primary" onClick={handleSubmit} disabled={loading}>
        {loading ? "Checking..." : "Run PA Pre-Check"}
      </button>

      {error && <div className="error-box">{error}</div>}

      {result && (
        <div className="result-box">
          <h3>Results for {result.payer} — CPT {result.cpt_code}</h3>

          <Section title="📋 Policy Requirements" items={result.policy_requirements} color="blue" />
          <Section title="✅ Documentation Present" items={result.documentation_present} color="green" />
          <Section title="❌ Documentation Missing" items={result.documentation_missing} color="red" />

          <div className="recommendation-box">
            <strong>Recommendation:</strong> {result.recommendation}
          </div>
          <div className="source-label">Source: {result.policy_source}</div>
        </div>
      )}
    </div>
  );
}

function Section({ title, items = [], color }) {
  if (!items.length) return null;
  return (
    <div className={`section-block section-block--${color}`}>
      <h4>{title}</h4>
      <ul>{items.map((item, i) => <li key={i}>{item}</li>)}</ul>
    </div>
  );
}