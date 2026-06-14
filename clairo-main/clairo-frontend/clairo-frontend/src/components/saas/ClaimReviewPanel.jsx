import { useEffect, useState } from "react";
import { SectionHeader } from "../ui";

const FIELDS = [
  { key: "payer", label: "Payer" },
  { key: "patient_id", label: "Patient ID" },
  { key: "cpt_codes", label: "CPT Codes", isCpt: true },
  { key: "denial_reason", label: "Denial Reason" },
  { key: "service_date", label: "Service Date" },
  { key: "billed_amount", label: "Billed Amount" },
  { key: "denied_amount", label: "Denied Amount" },
];

function toFormState(claim = {}) {
  const cpt = claim.cpt_codes;
  return {
    payer: claim.payer ?? "",
    patient_id: claim.patient_id ?? "",
    cpt_codes: Array.isArray(cpt) ? cpt.join(", ") : (cpt ?? ""),
    denial_reason: claim.denial_reason ?? "",
    service_date: claim.service_date ?? "",
    billed_amount: claim.billed_amount ?? "",
    denied_amount: claim.denied_amount ?? "",
  };
}

function toStructuredClaim(form) {
  const cptRaw = form.cpt_codes.trim();
  const cpt_codes = cptRaw.includes(",")
    ? cptRaw.split(",").map((s) => s.trim()).filter(Boolean)
    : cptRaw
      ? [cptRaw]
      : [];
  return {
    payer: form.payer || undefined,
    patient_id: form.patient_id || undefined,
    cpt_codes: cpt_codes.length ? cpt_codes : undefined,
    denial_reason: form.denial_reason || undefined,
    service_date: form.service_date || undefined,
    billed_amount: form.billed_amount || undefined,
    denied_amount: form.denied_amount || undefined,
  };
}

export default function ClaimReviewPanel({ uploadResult, onUpdateClaim }) {
  const [form, setForm] = useState(() =>
    toFormState(uploadResult?.structured_claim),
  );
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setForm(toFormState(uploadResult?.structured_claim));
    setSaved(false);
  }, [uploadResult]);

  if (!uploadResult?.structured_claim) return null;

  function handleChange(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  function handleSubmit(e) {
    e.preventDefault();
    onUpdateClaim?.(toStructuredClaim(form));
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2500);
  }

  return (
    <div className="panel claim-review-panel">
      <SectionHeader
        icon="✎"
        title="Review Claim Details"
        subtitle="Confirm extracted fields before generating an appeal"
      />

      <form className="claim-review-form" onSubmit={handleSubmit}>
        {FIELDS.map(({ key, label }) => (
          <label key={key} className="claim-review-field">
            <span className="claim-review-field__label">{label}</span>
            <input
              className="claim-review-field__input"
              type="text"
              value={form[key]}
              onChange={(e) => handleChange(key, e.target.value)}
              placeholder="—"
            />
          </label>
        ))}

        <div className="btn-row claim-review-panel__actions">
          <button type="submit" className="btn-saas">
            {saved ? "✓ Details Updated" : "Update Claim Details"}
          </button>
        </div>
      </form>
    </div>
  );
}
