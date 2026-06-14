import { useState } from "react";
import { retrievePolicy } from "../api";
import { Spinner, ErrorBox, SectionHeader } from "./ui";

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
        <p className="policy-source-meta">
          Source: {result.source ?? result.metadata}
        </p>
      )}
    </article>
  );
}

export default function PolicyPanel({ uploadResult, onPolicyRetrieved, embedded = false }) {
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
  const showEmptyState = !hasResults && !showNoMatches;

  const wrapperClass = embedded
    ? "appeal-workflow__evidence coverage-evidence-section"
    : "panel";

  return (
    <section className={wrapperClass}>
      <SectionHeader
        icon="📚"
        title="Coverage Evidence"
        subtitle="Policy citations and payer documentation supporting the generated appeal."
      />

      {hasResults && canRetrieve && (
        <button
          type="button"
          className="btn-secondary"
          onClick={handleRetrieve}
          disabled={loading}
        >
          {loading ? (
            <>
              <Spinner size={16} /> Retrieving…
            </>
          ) : (
            "Retrieve Coverage Evidence"
          )}
        </button>
      )}

      <ErrorBox message={error} />

      <div className="coverage-evidence-box">
        {loading && (
          <div className="coverage-evidence-box__loading" aria-busy="true">
            <Spinner size={22} />
            <span>Retrieving policy citations…</span>
          </div>
        )}

        {!loading && showEmptyState && (
          <div className="coverage-empty">
            <span className="coverage-empty__icon" aria-hidden="true">
              📚
            </span>
            <h3 className="coverage-empty__title">No coverage evidence yet</h3>
            <p className="coverage-empty__text">
              {canRetrieve
                ? "Generate or retrieve policy evidence to support this appeal letter."
                : "Add payer and CPT codes on Claim Intake to retrieve policy evidence."}
            </p>
            <button
              type="button"
              className="btn-saas"
              onClick={handleRetrieve}
              disabled={!canRetrieve || loading}
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
          <div className="policy-list policy-list--in-box">
            {results.map((r, i) => (
              <PolicyCitationCard
                key={i}
                result={r}
                index={i}
                payerName={payerName}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
