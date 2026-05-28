import { useState } from "react";
import { scoreQueue, scoreClaim } from "../api";
import { Spinner, ErrorBox, Badge, ConfidenceMeter, SectionHeader } from "./ui";

// Demo queue used when no upload is available yet
const DEMO_QUEUE = [
  { cpt_codes: ["29881"], payer: "UHC", documentation_notes: "Missing two failed conservative treatments" },
  { cpt_codes: ["27447"], payer: "Aetna", documentation_notes: "No prior auth on file" },
  { cpt_codes: ["93306"], payer: "Cigna", documentation_notes: "Echo without documented heart failure indication" },
  { cpt_codes: ["22612"], payer: "BCBS", documentation_notes: "Spinal fusion, documentation complete" },
  { cpt_codes: ["70553"], payer: "Humana", documentation_notes: "Brain MRI, incomplete notes" },
];

export default function RiskHeatmap({ uploadResult }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [heatmapData, setHeatmapData] = useState(null);
  const [singleRisk, setSingleRisk] = useState(null);
  const [mode, setMode] = useState("queue"); // "queue" | "single"

  async function handleScoreQueue() {
    setError(null);
    setLoading(true);
    setHeatmapData(null);
    setSingleRisk(null);
    setMode("queue");
    try {
      const data = await scoreQueue(DEMO_QUEUE);
      setHeatmapData(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleScoreCurrent() {
    if (!uploadResult?.structured_claim) return;
    setError(null);
    setLoading(true);
    setHeatmapData(null);
    setSingleRisk(null);
    setMode("single");
    const claim = uploadResult.structured_claim;
    const cptCodes = claim.cpt_codes;
    const cpts = Array.isArray(cptCodes) ? cptCodes : [cptCodes ?? ""];
    try {
      const data = await scoreClaim(cpts, claim.payer ?? "", claim.denial_reason ?? "");
      setSingleRisk(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const results = heatmapData?.results ?? [];

  return (
    <div className="panel">
      <SectionHeader
        icon="🌡"
        title="Denial Risk Heatmap"
        subtitle="Score claims 0–100 for denial probability before submission"
      />

      <div className="btn-row">
        <button className="btn-primary" onClick={handleScoreQueue} disabled={loading}>
          {loading && mode === "queue" ? <><Spinner size={16} /> Scoring…</> : "Score Demo Queue"}
        </button>
        {uploadResult?.structured_claim && (
          <button className="btn-secondary" onClick={handleScoreCurrent} disabled={loading}>
            {loading && mode === "single" ? <><Spinner size={16} /> Scoring…</> : "Score Uploaded Claim"}
          </button>
        )}
      </div>

      <ErrorBox message={error} />

      {/* Single claim score */}
      {singleRisk && (
        <div className="single-risk-card">
          <div className="field-row">
            <span className="field-label">Risk Score</span>
            <ConfidenceMeter score={singleRisk.risk_score} />
          </div>
          <div className="field-row">
            <span className="field-label">Risk Level</span>
            <Badge level={singleRisk.risk_level} />
          </div>
          {singleRisk.remediation && (
            <div className="field-row">
              <span className="field-label">Remediation</span>
              <span className="field-value">{singleRisk.remediation}</span>
            </div>
          )}
          {/* Fix: backend returns `rule_flags`, not `flags` */}
          {singleRisk.rule_flags && singleRisk.rule_flags.length > 0 && (
            <div className="field-row">
              <span className="field-label">Flags</span>
              <ul className="flag-list">
                {singleRisk.rule_flags.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Queue heatmap */}
      {heatmapData && (
        <>
          <div className="heatmap-summary">
            <div className="heatmap-stat high">
              <span className="stat-num">{heatmapData.high_risk_count ?? 0}</span>
              <span className="stat-label">High Risk</span>
            </div>
            <div className="heatmap-stat medium">
              <span className="stat-num">{heatmapData.medium_risk_count ?? 0}</span>
              <span className="stat-label">Medium Risk</span>
            </div>
            <div className="heatmap-stat low">
              <span className="stat-num">{heatmapData.low_risk_count ?? 0}</span>
              <span className="stat-label">Low Risk</span>
            </div>
            <div className="heatmap-stat total">
              <span className="stat-num">{heatmapData.total_claims ?? 0}</span>
              <span className="stat-label">Total Claims</span>
            </div>
          </div>

          <div className="heatmap-table-wrap">
            <table className="heatmap-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Payer</th>
                  <th>CPT</th>
                  <th>Risk Score</th>
                  <th>Level</th>
                  <th>Remediation</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i} className={`row-${(r.risk_level ?? "LOW").toLowerCase()}`}>
                    <td>{i + 1}</td>
                    <td>{r.payer ?? "N/A"}</td>
                    <td>{Array.isArray(r.cpt_codes) ? r.cpt_codes.join(", ") : r.cpt_codes ?? "N/A"}</td>
                    <td>
                      <ConfidenceMeter score={r.risk_score} />
                    </td>
                    <td><Badge level={r.risk_level} /></td>
                    <td className="remediation-cell">{r.remediation ?? "N/A"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
