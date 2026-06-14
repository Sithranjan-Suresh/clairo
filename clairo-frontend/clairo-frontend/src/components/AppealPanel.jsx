import { useState } from "react";
import { generateAppeal, getViability, exportAppealPdf, printAppealLetterPdf, retrievePolicy } from "../api";
import { Spinner, ErrorBox, ConfidenceMeter, SectionHeader } from "./ui";
import AppealConfidenceDisplay from "./AppealConfidenceDisplay";
import WorkflowStepper from "./saas/WorkflowStepper";
import { normalizeAppealConfidence } from "../utils/appealConfidence";

function formatLetterText(text) {
  return (text ?? "").replace(/\\n/g, "\n");
}

function PolicyCitationCard({ result, index, payerName }) {
  const excerpt = result.text ?? result.excerpt ?? result.highlight ?? null;
  const documentName = result.document_name ?? result.source ?? result.document ?? "Unknown document";
  const section = result.section_number ?? result.section ?? result.chunk_index ?? index + 1;
  const page = result.page_number ?? result.page ?? null;
  const cardPayer = result.payer ?? payerName ?? "—";

  return (
    <article className="policy-card policy-card--evidence">
      <div className="policy-card-header">
        <span className="policy-badge">Section {section}</span>
        <span className="policy-source">{documentName}</span>
      </div>
      <div className="policy-meta-grid">
        <div className="policy-meta-item">
          <span className="policy-meta-item__label">Payer</span>
          <span className="policy-meta-item__value">{cardPayer}</span>
        </div>
        <div className="policy-meta-item">
          <span className="policy-meta-item__label">Document</span>
          <span className="policy-meta-item__value">{documentName}</span>
        </div>
        <div className="policy-meta-item">
          <span className="policy-meta-item__label">Section</span>
          <span className="policy-meta-item__value">{section}</span>
        </div>
        <div className="policy-meta-item">
          <span className="policy-meta-item__label">Page</span>
          <span className="policy-meta-item__value">{page ?? "—"}</span>
        </div>
      </div>
      {result.score != null && (
        <div className="field-row policy-meta-score">
          <span className="field-label">Relevance</span>
          <span className="field-value">{(result.score * 100).toFixed(1)}%</span>
        </div>
      )}
      <div className="policy-text policy-text--excerpt">
        {excerpt ?? "No excerpt available."}
      </div>
      {(result.source || result.metadata) && (
        <p className="policy-source-meta">Source: {result.source ?? result.metadata}</p>
      )}
    </article>
  );
}

function CoverageEvidenceBlock({ uploadResult, onPolicyRetrieved }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  const claim = uploadResult?.structured_claim ?? {};
  const payerName = claim.payer ?? null;
  const canRetrieve = Boolean(claim.payer && claim.cpt_codes);

  async function handleRetrieve() {
    if (!canRetrieve) return;
    setError(null);
    setLoading(true);
    setResults(null);
    try {
      const cptCodes = claim.cpt_codes;
      const cpt = Array.isArray(cptCodes) ? cptCodes[0] : cptCodes ?? "";
      const data = await retrievePolicy(
        claim.payer ?? "",
        cpt,
        claim.denial_reason ?? "",
        uploadResult.classification ?? "",
      );
      const list = data.results ?? [];
      setResults(list);
      onPolicyRetrieved?.(list.length, list[0]?.source);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const showNoMatches = results !== null && results.length === 0;
  const hasResults = results && results.length > 0;

  return (
    <div className="appeal-coverage-block" data-testid="coverage-evidence-section">
      <SectionHeader
        icon="📚"
        title="Coverage of Evidence"
        subtitle="Policy citations and payer documentation supporting the generated appeal."
      />

      <ErrorBox message={error} />

      <div className="coverage-evidence-box" data-testid="coverage-evidence-box">
        {loading && (
          <div className="coverage-evidence-box__loading" aria-busy="true">
            <Spinner size={22} />
            <span>Retrieving policy citations…</span>
          </div>
        )}

        {!loading && !hasResults && !showNoMatches && (
          <div className="coverage-empty">
            <span className="coverage-empty__icon" aria-hidden="true">📚</span>
            <h3 className="coverage-empty__title">No coverage evidence yet</h3>
            <p className="coverage-empty__text">
              {canRetrieve
                ? "Retrieve policy citations to support this appeal letter."
                : "Add payer and CPT codes on Claim Intake to retrieve policy evidence."}
            </p>
            <button
              type="button"
              className="btn-saas"
              onClick={handleRetrieve}
              disabled={!canRetrieve}
            >
              Retrieve Coverage Evidence
            </button>
          </div>
        )}

        {!loading && showNoMatches && (
          <div className="coverage-empty coverage-empty--muted">
            <h3 className="coverage-empty__title">No matching policies found</h3>
            <p className="coverage-empty__text">
              No policy sections matched this payer and procedure combination.
            </p>
            <button type="button" className="btn-secondary" onClick={handleRetrieve}>
              Try Again
            </button>
          </div>
        )}

        {!loading && hasResults && (
          <>
            <div className="coverage-evidence-box__toolbar">
              <span className="coverage-evidence-box__count">
                {results.length} citation{results.length !== 1 ? "s" : ""} found
              </span>
              <button type="button" className="btn-copy" onClick={handleRetrieve}>
                Refresh
              </button>
            </div>
            <div className="policy-list policy-list--in-box">
              {results.map((r, i) => (
                <PolicyCitationCard key={i} result={r} index={i} payerName={payerName} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function AppealPanel({
  uploadResult,
  onPolicyRetrieved,
  appealData,
  appealViability,
  appealLetterText,
  onAppealGenerated,
  onAppealLetterChange,
  onExportCompleted,
  onResetAppeal,
}) {
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editDraft, setEditDraft] = useState("");
  const [generateSuccess, setGenerateSuccess] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);

  const canGenerate = uploadResult?.structured_claim && uploadResult?.classification;
  const hasAppeal = Boolean(appealLetterText || appealData?.appeal_letter);
  const formattedLetter = formatLetterText(appealLetterText ?? appealData?.appeal_letter ?? "");
  const viability = appealViability;

  async function handleGenerate() {
    setError(null);
    setGenerateSuccess(false);
    setIsEditing(false);
    setLoading(true);
    try {
      const result = await generateAppeal(
        uploadResult.structured_claim,
        uploadResult.classification,
      );

      let nextViability = null;
      if (result.confidence_score != null) {
        nextViability = await getViability(
          result.confidence_score,
          uploadResult.classification,
          uploadResult.structured_claim.payer ?? "Unknown",
        );
      }

      onAppealGenerated?.(result, nextViability);
      setGenerateSuccess(true);
      window.setTimeout(() => setGenerateSuccess(false), 4000);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleStartEdit() {
    setEditDraft(formattedLetter);
    setIsEditing(true);
  }

  function handleSaveEdit() {
    onAppealLetterChange?.(editDraft);
    setIsEditing(false);
  }

  function handleCancelEdit() {
    setEditDraft(formattedLetter);
    setIsEditing(false);
  }

  function handleCopy() {
    navigator.clipboard.writeText(formattedLetter).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    });
  }

  async function handleExportPdf() {
    if (!formattedLetter) return;
    setExportError(null);
    setExportSuccess(false);
    setExporting(true);
    const claim = uploadResult?.structured_claim ?? {};

    try {
      const result = await exportAppealPdf({
        appeal_letter: formattedLetter,
        structured_claim: claim,
        classification: uploadResult?.classification,
        confidence_score: normalizeAppealConfidence(appealData?.confidence_score) ?? 0,
      });

      if (result?.blob) {
        const url = URL.createObjectURL(result.blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = result.filename ?? "clairo-appeal-letter.pdf";
        a.click();
        URL.revokeObjectURL(url);
      } else if (result?.download_url) {
        window.open(result.download_url, "_blank", "noopener,noreferrer");
      } else {
        printAppealLetterPdf(formattedLetter, claim);
      }

      onExportCompleted?.();
      setExportSuccess(true);
      window.setTimeout(() => setExportSuccess(false), 4000);
    } catch {
      try {
        printAppealLetterPdf(formattedLetter, claim);
        onExportCompleted?.();
        setExportSuccess(true);
        window.setTimeout(() => setExportSuccess(false), 4000);
      } catch (e) {
        setExportError(e.message ?? "Export failed. Try again or copy the letter.");
      }
    } finally {
      setExporting(false);
    }
  }

  function handleReset() {
    setIsEditing(false);
    setEditDraft("");
    setGenerateSuccess(false);
    setExportSuccess(false);
    setExportError(null);
    setError(null);
    onResetAppeal?.();
  }

  return (
    <div className="appeal-page-sections">
      <WorkflowStepper uploadResult={uploadResult} />

      <section className="panel panel--primary appeal-section appeal-section--primary">
        <CoverageEvidenceBlock
          uploadResult={uploadResult}
          onPolicyRetrieved={onPolicyRetrieved}
        />
      </section>

      <section className="panel appeal-section appeal-section--secondary">
        <SectionHeader
          icon="⚖"
          title="Generate Appeal Letter"
          subtitle="Generate a citation-backed appeal grounded in payer policy"
        />

        <div className="btn-row appeal-actions">
        {canGenerate && (
          <button className="btn-primary" onClick={handleGenerate} disabled={loading || isEditing}>
            {loading ? (
              <>
                <Spinner size={16} /> Generating Appeal…
              </>
            ) : (
              "Generate Appeal Letter"
            )}
          </button>
        )}
        {hasAppeal && !isEditing && (
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleStartEdit}
              disabled={loading || exporting}
            >
              Edit
            </button>
            <button
              type="button"
              className="btn-saas"
              onClick={handleExportPdf}
              disabled={exporting || loading}
            >
              {exporting ? (
                <>
                  <Spinner size={14} /> Exporting…
                </>
              ) : (
                "Export PDF"
              )}
            </button>
            <button type="button" className="btn-copy" onClick={handleCopy}>
              {copied ? "✓ Copied!" : "Copy"}
            </button>
            <button
              type="button"
              className="btn-copy appeal-actions__reset"
              onClick={handleReset}
              disabled={loading || exporting}
            >
              Reset
            </button>
          </>
        )}
        {isEditing && (
          <>
            <button type="button" className="btn-primary" onClick={handleSaveEdit}>
              Save
            </button>
            <button type="button" className="btn-secondary" onClick={handleCancelEdit}>
              Cancel
            </button>
          </>
        )}
      </div>

      <ErrorBox message={error} />

      {generateSuccess && (
        <p className="appeal-status appeal-status--success" role="status">
          Appeal letter generated successfully. You can review, edit, or export below.
        </p>
      )}

      {exportSuccess && (
        <p className="appeal-status appeal-status--success" role="status">
          Export completed. Workflow is fully complete.
        </p>
      )}

      {hasAppeal && (
        <>
          <div className="appeal-meta">
            <div className="field-row">
              <span className="field-label">Appeal Confidence</span>
              <AppealConfidenceDisplay score={appealData?.confidence_score} />
            </div>
            {appealData?.confidence_rationale && (
              <div className="field-row">
                <span className="field-label">Rationale</span>
                <span className="field-value">{appealData.confidence_rationale}</span>
              </div>
            )}
            {viability && (
              <>
                <div className="field-row">
                  <span className="field-label">Viability Rating</span>
                  <span
                    className={`field-value tag viability-${(viability.viability ?? "").toLowerCase()}`}
                  >
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

          <div className="letter-header">
            <span className="field-label">
              {isEditing ? "Edit Appeal Letter" : "Generated Appeal Letter"}
            </span>
          </div>
          <ErrorBox message={exportError} />
          {isEditing ? (
            <textarea
              className="letter-box letter-box--editable"
              value={editDraft}
              onChange={(e) => setEditDraft(e.target.value)}
              aria-label="Edit appeal letter"
              spellCheck
            />
          ) : (
            <pre className="letter-box letter-box--compact">{formattedLetter}</pre>
          )}
        </>
      )}
      </section>
    </div>
  );
}
