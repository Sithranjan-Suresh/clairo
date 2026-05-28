import { useState } from "react";
import { generateAppeal, getViability, exportAppealPDF } from "../api";
import { Spinner, ErrorBox, ConfidenceMeter, SectionHeader } from "./ui";

export default function AppealPanel({ uploadResult }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [appealData, setAppealData] = useState(null);
  const [viability, setViability] = useState(null);
  const [copied, setCopied] = useState(false);

  const canGenerate = uploadResult?.structured_claim && uploadResult?.classification;

  async function handleGenerate() {
    setError(null);
    setLoading(true);
    setAppealData(null);
    setViability(null);
    try {
      const result = await generateAppeal(
        uploadResult.structured_claim,
        uploadResult.classification
      );
      setAppealData(result);

      // Also fetch viability
      if (result.confidence_score != null) {
        const v = await getViability(
          result.confidence_score,
          uploadResult.classification,
          uploadResult.structured_claim.payer ?? "Unknown"
        );
        setViability(v);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  async function handleExportPDF() {
  await exportAppealPDF(
    uploadResult.structured_claim,
    uploadResult.classification,
    appealData.appeal_letter,
    appealData.confidence_score
  );
}

  function handleCopy() {
    const text = appealData?.appeal_letter ?? "";
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  const letter = appealData?.appeal_letter ?? "";
  // Render \n as actual line breaks
  const formattedLetter = letter.replace(/\\n/g, "\n");

  return (
    <div className="panel">
      <SectionHeader icon="⚖" title="Appeal Letter Generator" subtitle="Citation-backed appeal grounded in payer policy" />

      {!canGenerate && (
        <p className="hint">Upload a denial document first to enable appeal generation.</p>
      )}

      {canGenerate && (
        <button
          className="btn-primary"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? <><Spinner size={16} /> Generating Appeal…</> : "Generate Appeal Letter"}
        </button>
      )}

      <ErrorBox message={error} />

      {appealData && (
        <>
          <div className="appeal-meta">
            <div className="field-row">
              <span className="field-label">Confidence Score</span>
              <ConfidenceMeter score={appealData.confidence_score} />
            </div>
            {appealData.confidence_rationale && (
              <div className="field-row">
                <span className="field-label">Rationale</span>
                <span className="field-value">{appealData.confidence_rationale}</span>
              </div>
            )}
            {viability && (
              <>
                {/* Fix: backend returns `viability` and `recovery_probability`, not `viability_rating`/`recommendation` */}
                <div className="field-row">
                  <span className="field-label">Viability Rating</span>
                  <span className={`field-value tag viability-${(viability.viability ?? "").toLowerCase()}`}>
                    {viability.viability ?? "N/A"}
                  </span>
                </div>
                {viability.recovery_probability && (
                  <div className="field-row">
                    <span className="field-label">Recovery Probability</span>
                    <span className="field-value">{viability.recovery_probability}</span>
                  </div>
                )}
                {viability.viability_score != null && (
                  <div className="field-row">
                    <span className="field-label">Viability Score</span>
                    <ConfidenceMeter score={viability.viability_score} />
                  </div>
                )}
              </>
            )}
          </div>

          <div className="divider" />

          <div className="letter-header">
            <span className="field-label">Generated Appeal Letter</span>
            <button className="btn-copy" onClick={handleCopy}>
              {copied ? "✓ Copied!" : "Copy"}
            </button>
            <button className="btn-secondary" onClick={handleExportPDF}>
  ⬇ Download PDF
</button>
          </div>
          <pre className="letter-box">{formattedLetter}</pre>
        </>
      )}
    </div>
  );
}
