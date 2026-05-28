import { Badge, ConfidenceMeter, SectionHeader } from "./ui";

function Field({ label, value }) {
  return (
    <div className="field-row">
      <span className="field-label">{label}</span>
      <span className="field-value">{value ?? "N/A"}</span>
    </div>
  );
}

export default function ClaimDetails({ uploadResult }) {
  if (!uploadResult) return null;

  const { filename, structured_claim = {}, classification, risk_score, risk_level } = uploadResult;
  const cptCodes = structured_claim.cpt_codes;
  const cptDisplay = Array.isArray(cptCodes)
    ? cptCodes.join(", ")
    : cptCodes ?? "N/A";

  return (
    <div className="panel">
      <SectionHeader icon="🗂" title="Extracted Claim Details" subtitle="Automatically parsed from uploaded document" />

      <div className="fields-grid">
        <Field label="File Name" value={filename} />
        <Field label="Payer" value={structured_claim.payer} />
        <Field label="Patient ID" value={structured_claim.patient_id} />
        <Field label="CPT Codes" value={cptDisplay} />
        <Field label="Denial Reason" value={structured_claim.denial_reason} />
        <Field label="Billed Amount" value={structured_claim.billed_amount} />
        <Field label="Denied Amount" value={structured_claim.denied_amount} />
        <Field label="Service Date" value={structured_claim.service_date} />
      </div>

      <div className="divider" />

      <div className="classification-row">
        <div className="field-row">
          <span className="field-label">Denial Category</span>
          <span className="field-value tag">{classification ?? "N/A"}</span>
        </div>
        <div className="field-row">
          <span className="field-label">Risk Level</span>
          <Badge level={risk_level} />
        </div>
        <div className="field-row">
          <span className="field-label">Risk Score</span>
          <ConfidenceMeter score={risk_score} />
        </div>
      </div>
    </div>
  );
}
