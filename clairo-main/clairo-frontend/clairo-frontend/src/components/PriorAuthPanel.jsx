import { useEffect, useRef, useState } from "react";
import { checkPriorAuthorizationDocuments } from "../api";
import { Spinner, ErrorBox, SectionHeader } from "./ui";
import ClaimInfoBanner from "./ClaimInfoBanner";

const CPT_PATTERN = /^\d{5}(-\d{2})?$/;
const ICD10_PATTERN = /^[A-TV-Z][0-9][0-9AB](\.[0-9A-Z]{1,4})?$/i;
const ACCEPTED_TYPES = ".pdf,.txt,.doc,.docx";
const PRIOR_AUTH_STORAGE_KEY = "clairo_prior_auth_state";

function loadStoredPriorAuthState() {
  try {
    const raw = sessionStorage.getItem(PRIOR_AUTH_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function restoreUploadedFiles(fileMetadata) {
  if (!Array.isArray(fileMetadata) || fileMetadata.length === 0) return [];
  return fileMetadata.map((item) => ({
    id: item.id,
    name: item.name,
    size: item.size,
    status: item.status ?? "ready",
    file: null,
  }));
}

function firstCpt(cptCodes) {
  if (Array.isArray(cptCodes)) return cptCodes[0] ?? "";
  return cptCodes ?? "";
}

function buildPrefill(uploadResult) {
  const c = uploadResult?.structured_claim ?? {};
  return {
    payer: c.payer ?? "",
    cpt_code: firstCpt(c.cpt_codes),
    diagnosis_code: c.diagnosis_code ?? c.icd10 ?? "",
    procedure_name: c.procedure_name ?? "",
    clinical_notes: "",
  };
}

function formatFileSize(bytes) {
  if (!bytes && bytes !== 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function PaRequiredBadge({ value }) {
  if (value === true) {
    return <span className="pa-packet-badge pa-packet-badge--required">Required</span>;
  }
  if (value === false) {
    return <span className="pa-packet-badge pa-packet-badge--not-required">Not Required</span>;
  }
  return <span className="pa-packet-badge pa-packet-badge--unknown">Unknown</span>;
}

function StatusBadge({ status }) {
  const raw = String(status ?? "unclear").toLowerCase();
  const variant =
    raw === "met" ? "met" : raw === "missing" ? "missing" : "unclear";
  const label = raw === "met" ? "Met" : raw === "missing" ? "Missing" : "Unclear";
  return (
    <span className={`pa-status-badge pa-status-badge--${variant}`}>{label}</span>
  );
}

function SummaryCard({ label, value, children }) {
  return (
    <div className="pa-summary-card">
      <span className="pa-summary-card__label">{label}</span>
      <div className="pa-summary-card__value">{children ?? value}</div>
    </div>
  );
}

function ResultBlock({ title, children, className = "" }) {
  return (
    <section className={`pa-result-block ${className}`.trim()}>
      <h4 className="pa-result-block__title">{title}</h4>
      <div className="pa-result-block__body">{children}</div>
    </section>
  );
}

export default function PriorAuthPanel({ uploadResult, onGoToIntake, isActive = true }) {
  const hasClaim = !!uploadResult?.structured_claim;
  const fileInputRef = useRef(null);
  const storedStateRef = useRef(loadStoredPriorAuthState());
  const [form, setForm] = useState(() => {
    if (storedStateRef.current?.form) return storedStateRef.current.form;
    return buildPrefill(uploadResult);
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [validationMessage, setValidationMessage] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState(() =>
    restoreUploadedFiles(storedStateRef.current?.fileMetadata),
  );
  const [filesNeedReupload, setFilesNeedReupload] = useState(() =>
    Boolean(storedStateRef.current?.fileMetadata?.length),
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(() => storedStateRef.current?.error ?? null);
  const [result, setResult] = useState(() => storedStateRef.current?.result ?? null);

  useEffect(() => {
    if (!hasClaim) return;
    setForm((prev) => {
      const hasUserInput =
        prev.payer?.trim() ||
        prev.cpt_code?.trim() ||
        prev.diagnosis_code?.trim() ||
        prev.clinical_notes?.trim() ||
        prev.procedure_name?.trim();
      if (hasUserInput) return prev;
      return buildPrefill(uploadResult);
    });
  }, [uploadResult, hasClaim]);

  useEffect(() => {
    if (!isActive) {
      setLoading(false);
    }
  }, [isActive]);

  useEffect(() => {
    sessionStorage.setItem(
      PRIOR_AUTH_STORAGE_KEY,
      JSON.stringify({
        form,
        fileMetadata: uploadedFiles.map(({ id, name, size, status }) => ({
          id,
          name,
          size,
          status,
        })),
        result,
        error,
      }),
    );
  }, [form, uploadedFiles, result, error]);

  function handleChange(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => ({ ...prev, [key]: null }));
    setValidationMessage(null);
    setResult(null);
  }

  function handleAddFiles(fileList) {
    if (!fileList?.length) return;
    const next = Array.from(fileList).map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${Math.random()}`,
      file,
      name: file.name,
      size: file.size,
      status: "ready",
    }));
    setUploadedFiles((prev) => [...prev, ...next]);
    setFilesNeedReupload(false);
    setValidationMessage(null);
    setResult(null);
  }

  function removeFile(id) {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
    setResult(null);
  }

  function validate() {
    const errs = {};
    if (!form.payer?.trim()) errs.payer = "Payer is required";
    if (!form.cpt_code?.trim()) errs.cpt_code = "CPT code is required";
    else if (!CPT_PATTERN.test(form.cpt_code.trim())) {
      errs.cpt_code = "Use 5-digit CPT (e.g. 29881)";
    }
    const icd = form.diagnosis_code?.trim();
    if (icd && !ICD10_PATTERN.test(icd)) {
      errs.diagnosis_code = "Use valid ICD-10 (e.g. M17.11)";
    }
    if (!uploadedFiles.length && !form.clinical_notes?.trim()) {
      errs.documents = "Upload at least one document or add clinical context.";
    }
    setFieldErrors(errs);
    if (Object.keys(errs).length > 0) {
      setValidationMessage("Please fix the highlighted fields before generating the packet.");
      return false;
    }
    setValidationMessage(null);
    return true;
  }

  async function handleGenerate() {
    if (!validate()) return;

    const missingFileObjects = uploadedFiles.some((item) => !item.file);
    if (missingFileObjects) {
      setError(
        "Uploaded file names were restored, but please re-upload files before generating again.",
      );
      return;
    }

    setError(null);
    setValidationMessage(null);
    setLoading(true);
    setResult(null);
    setUploadedFiles((prev) =>
      prev.map((f) => ({ ...f, status: "uploading" })),
    );

    try {
      const formData = new FormData();
      formData.append("payer", form.payer.trim());
      formData.append("cpt_codes", form.cpt_code.trim());
      formData.append("diagnosis_codes", form.diagnosis_code?.trim() ?? "");
      formData.append("clinical_notes", form.clinical_notes?.trim() ?? "");

      if (import.meta.env.DEV) {
        console.info("[Prior Auth] submitting", {
          payer: form.payer.trim(),
          cpt: form.cpt_code.trim(),
          diagnosis: form.diagnosis_code?.trim() ?? "",
          fileCount: uploadedFiles.length,
          fileNames: uploadedFiles.map((f) => f.name),
        });
      }

      uploadedFiles.forEach(({ file }) => {
        formData.append("files", file);
      });

      const data = await checkPriorAuthorizationDocuments(formData);
      setResult(data);
      setUploadedFiles((prev) =>
        prev.map((f) => ({ ...f, status: "processed" })),
      );
    } catch (e) {
      setError(
        e.message?.includes("Failed to fetch")
          ? "Prior auth service unavailable. Ensure the backend is running."
          : e.message ?? "Prior authorization packet generation failed.",
      );
      setUploadedFiles((prev) =>
        prev.map((f) => ({ ...f, status: f.status === "uploading" ? "failed" : f.status })),
      );
    } finally {
      setLoading(false);
    }
  }

  const canSubmit =
    form.payer?.trim() &&
    form.cpt_code?.trim() &&
    (uploadedFiles.length > 0 || form.clinical_notes?.trim()) &&
    !loading;

  const packet = result?.packet ?? null;
  const missingCount = Array.isArray(packet?.documentation_missing)
    ? packet.documentation_missing.length
    : 0;
  const docStatus =
    missingCount === 0 && packet
      ? "Complete"
      : missingCount > 0
        ? `${missingCount} gap${missingCount !== 1 ? "s" : ""}`
        : "Pending";

  return (
    <div className="panel module-page prior-auth-packet">
      <SectionHeader
        icon="📋"
        title="Prior Authorization"
        subtitle="Build a multi-document prior authorization packet from clinical evidence and payer policy."
      />

      {!hasClaim && <ClaimInfoBanner onGoToIntake={onGoToIntake} />}

      {!result && !loading && (
        <div className="pa-empty-state module-card">
          <p className="pa-empty-state__text">
            Upload clinical documents — notes, imaging, PT records, referrals, operative reports,
            and denial letters — to generate an organized prior authorization packet for review.
          </p>
        </div>
      )}

      <div className="module-card pa-section">
        <h3 className="module-card__title font-ui">1. Request Details</h3>
        <div className="prior-auth-form claim-review-form">
          <label className="claim-review-field">
            <span className="claim-review-field__label">Payer *</span>
            <input
              className="claim-review-field__input"
              value={form.payer}
              onChange={(e) => handleChange("payer", e.target.value)}
              placeholder="e.g. UnitedHealthcare"
            />
            {fieldErrors.payer && <span className="field-error">{fieldErrors.payer}</span>}
          </label>

          <label className="claim-review-field">
            <span className="claim-review-field__label">CPT Code *</span>
            <input
              className="claim-review-field__input"
              value={form.cpt_code}
              onChange={(e) => handleChange("cpt_code", e.target.value)}
              placeholder="e.g. 29881"
            />
            {fieldErrors.cpt_code && <span className="field-error">{fieldErrors.cpt_code}</span>}
          </label>

          <label className="claim-review-field">
            <span className="claim-review-field__label">Diagnosis Code / ICD-10</span>
            <input
              className="claim-review-field__input"
              value={form.diagnosis_code}
              onChange={(e) => handleChange("diagnosis_code", e.target.value)}
              placeholder="e.g. M17.11"
            />
            {fieldErrors.diagnosis_code && (
              <span className="field-error">{fieldErrors.diagnosis_code}</span>
            )}
          </label>

          <label className="claim-review-field">
            <span className="claim-review-field__label">Requested Service / Procedure</span>
            <input
              className="claim-review-field__input"
              value={form.procedure_name}
              onChange={(e) => handleChange("procedure_name", e.target.value)}
              placeholder="e.g. Knee arthroscopy"
            />
          </label>
        </div>
      </div>

      <div className="module-card pa-section">
        <h3 className="module-card__title font-ui">2. Upload Supporting Documents</h3>
        <p className="pa-section__helper">
          Clinical notes, imaging reports, PT notes, referrals, operative reports, and denial letters.
        </p>

        <div
          className="pa-upload-zone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            handleAddFiles(e.dataTransfer.files);
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            multiple
            className="pa-upload-zone__input"
            onChange={(e) => {
              handleAddFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            className="btn-secondary"
            onClick={() => fileInputRef.current?.click()}
          >
            Upload clinical documents
          </button>
          <span className="pa-upload-zone__hint">PDF, TXT, DOCX · drag and drop supported</span>
        </div>

        {fieldErrors.documents && (
          <span className="field-error">{fieldErrors.documents}</span>
        )}

        {uploadedFiles.length > 0 && (
          <ul className="pa-file-list">
            {uploadedFiles.map((item) => (
              <li key={item.id} className="pa-file-card">
                <div className="pa-file-card__meta">
                  <span className="pa-file-card__name">{item.name}</span>
                  <span className="pa-file-card__size">{formatFileSize(item.size)}</span>
                </div>
                <div className="pa-file-card__actions">
                  <span className={`pa-file-card__status pa-file-card__status--${item.status}`}>
                    {item.status}
                  </span>
                  <button
                    type="button"
                    className="btn-copy"
                    onClick={() => removeFile(item.id)}
                    disabled={loading}
                  >
                    Remove
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="module-card pa-section">
        <h3 className="module-card__title font-ui">3. Additional Clinical Context</h3>
        <p className="pa-section__helper">Optional — supplement uploaded documents with brief context.</p>
        <textarea
          className="claim-review-field__input claim-review-field__textarea pa-notes-field"
          value={form.clinical_notes}
          onChange={(e) => handleChange("clinical_notes", e.target.value)}
          placeholder="Any additional clinical context not captured in uploaded documents..."
          rows={3}
        />
      </div>

      <div className="module-card pa-section">
        <h3 className="module-card__title font-ui">4. Generate Prior Authorization Packet</h3>
        <div className="btn-row">
          <button
            type="button"
            className="btn-primary"
            disabled={loading}
            onClick={handleGenerate}
          >
            {loading ? (
              <>
                <Spinner size={16} /> Generating packet…
              </>
            ) : (
              "Generate Prior Auth Packet"
            )}
          </button>
        </div>
        {!canSubmit && !loading && (
          <p className="pa-section__helper pa-submit-hint">
            Enter payer and CPT code, then upload at least one document or add clinical notes.
          </p>
        )}
      </div>

      <ErrorBox message={validationMessage} />
      <ErrorBox message={error} />
      {filesNeedReupload && uploadedFiles.length > 0 && (
        <div className="claim-info-banner">
          <span className="claim-info-banner__icon">⚠</span>
          <span className="claim-info-banner__text">
            Uploaded file names were restored, but please re-upload files before generating again.
          </span>
        </div>
      )}

      {loading && (
        <div className="loading-skeleton panel" aria-busy="true">
          <div className="loading-skeleton__bar loading-skeleton__bar--lg" />
          <div className="loading-skeleton__bar" />
        </div>
      )}

      {packet && !loading && (
        <div className="pa-results">
          <div className="pa-summary-grid">
            <SummaryCard label="PA Required">
              <PaRequiredBadge value={packet.pa_required} />
            </SummaryCard>
            <SummaryCard label="Confidence" value={`${packet.confidence ?? 0}%`} />
            <SummaryCard label="Documentation Status" value={docStatus} />
            <SummaryCard label="Missing Items" value={String(missingCount)} />
          </div>

          {result.warnings?.length > 0 && (
            <div className="pa-warnings module-card">
              <h4 className="module-card__title font-ui">Processing warnings</h4>
              <ul className="pa-warnings__list">
                {result.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {packet.provider_ready_summary && (
            <ResultBlock title="Provider-Ready Summary">
              <p className="pa-result-text">{packet.provider_ready_summary}</p>
            </ResultBlock>
          )}

          {packet.medical_necessity_summary && (
            <ResultBlock title="Medical Necessity Summary">
              <p className="pa-result-text">{packet.medical_necessity_summary}</p>
            </ResultBlock>
          )}

          {packet.policy_requirements?.length > 0 && (
            <ResultBlock title="Policy Requirements Checklist">
              <ul className="pa-checklist">
                {packet.policy_requirements.map((req, idx) => (
                  <li key={idx} className="pa-checklist__item">
                    <div className="pa-checklist__head">
                      <span className="pa-checklist__requirement">{req.requirement}</span>
                      <StatusBadge status={req.status} />
                    </div>
                    {req.supporting_evidence && (
                      <p className="pa-checklist__evidence">
                        <strong>Supporting evidence:</strong> {req.supporting_evidence}
                      </p>
                    )}
                    {req.source_document && (
                      <p className="pa-checklist__source">
                        <strong>Source:</strong> {req.source_document}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </ResultBlock>
          )}

          {packet.documentation_present?.length > 0 && (
            <ResultBlock title="Documentation Present">
              <ul className="pa-doc-list">
                {packet.documentation_present.map((doc, idx) => (
                  <li key={idx} className="pa-doc-list__item">
                    <strong>{doc.document ?? doc}</strong>
                    {Array.isArray(doc.key_findings) && doc.key_findings.length > 0 && (
                      <ul>
                        {doc.key_findings.map((finding, i) => (
                          <li key={i}>{finding}</li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </ResultBlock>
          )}

          {packet.documentation_missing?.length > 0 && (
            <ResultBlock title="Missing Documentation" className="pa-result-block--missing">
              <ul className="pa-missing-list">
                {packet.documentation_missing.map((item, idx) => (
                  <li key={idx} className="pa-missing-list__item">
                    <span className="pa-missing-list__title">
                      {item.missing_item ?? item}
                    </span>
                    {item.why_needed && (
                      <p className="pa-missing-list__why">
                        <strong>Why needed:</strong> {item.why_needed}
                      </p>
                    )}
                    {item.recommended_action && (
                      <p className="pa-missing-list__action">
                        <strong>Recommended action:</strong> {item.recommended_action}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </ResultBlock>
          )}

          {packet.clinical_evidence_by_document?.length > 0 && (
            <ResultBlock title="Evidence by Uploaded Document">
              <div className="pa-evidence-grid">
                {packet.clinical_evidence_by_document.map((block, idx) => (
                  <div key={idx} className="pa-evidence-card">
                    <h5 className="pa-evidence-card__title">{block.document_name}</h5>
                    <ul className="pa-evidence-card__list">
                      {(block.evidence_found ?? []).map((ev, i) => (
                        <li key={i}>{ev}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </ResultBlock>
          )}

          {packet.recommended_next_steps?.length > 0 && (
            <ResultBlock title="Recommended Next Steps">
              <ol className="pa-steps-list">
                {packet.recommended_next_steps.map((step, idx) => (
                  <li key={idx}>{step}</li>
                ))}
              </ol>
            </ResultBlock>
          )}

          {packet.doctor_review_notes && (
            <ResultBlock title="Doctor Review Notes">
              <p className="pa-result-text">{packet.doctor_review_notes}</p>
            </ResultBlock>
          )}

          {result.policy_source && (
            <p className="pa-policy-source">
              Policy reference: <strong>{result.policy_source}</strong>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
