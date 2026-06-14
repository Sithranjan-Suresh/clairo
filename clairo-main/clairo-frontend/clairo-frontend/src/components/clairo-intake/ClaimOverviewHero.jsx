import { Badge } from "../ui";
import AppealConfidenceDisplay from "../AppealConfidenceDisplay";
import { deriveWorkflowIndex } from "../saas/WorkflowStepper";
import {
  formatLabel,
  formatCurrency,
  formatCptCodes,
  displayValue,
  getWorkflowStage,
  deriveAppealReadiness,
} from "./claimIntakeUtils";

const STEPS = [
  "Upload",
  "Extract",
  "Classify",
  "Retrieve Policy",
  "Generate Appeal",
  "Export",
];

export default function ClaimOverviewHero({ uploadResult }) {
  if (!uploadResult) return null;

  const claim = uploadResult.structured_claim ?? {};
  const recoverable = formatCurrency(claim.denied_amount ?? claim.billed_amount);
  const category = uploadResult.classification
    ? formatLabel(uploadResult.classification)
    : "Pending classification";
  const appealReadiness = deriveAppealReadiness(uploadResult);
  const workflowStage = getWorkflowStage(uploadResult);
  const stepIndex = deriveWorkflowIndex(uploadResult);

  return (
    <section className="claim-hero glass-panel" aria-label="Claim overview">
      <div className="claim-hero__top">
        <div className="claim-hero__identity">
          <span className="claim-hero__payer">{displayValue(claim.payer)}</span>
          <span className="claim-hero__category-pill">{category}</span>
        </div>
        <div className="claim-hero__stage">
          <span className="claim-hero__stage-label">Current stage</span>
          <span className="claim-hero__stage-value">{workflowStage}</span>
        </div>
      </div>

      <div className="claim-hero__amount-block">
        <span className="claim-hero__amount-label">Recoverable Amount</span>
        <span className="claim-hero__amount">{recoverable}</span>
      </div>

      <div className="claim-hero__grid">
        <div className="claim-hero__stat">
          <span className="claim-hero__stat-label">Patient ID</span>
          <span className="claim-hero__stat-value">{displayValue(claim.patient_id)}</span>
        </div>
        <div className="claim-hero__stat">
          <span className="claim-hero__stat-label">CPT Code</span>
          <span className="claim-hero__stat-value">{formatCptCodes(claim.cpt_codes)}</span>
        </div>
        <div className="claim-hero__stat">
          <span className="claim-hero__stat-label">Risk Level</span>
          <Badge level={uploadResult.risk_level ?? "—"} />
        </div>
        <div className="claim-hero__stat">
          <span className="claim-hero__stat-label">Appeal Confidence</span>
          {uploadResult.appeal_confidence != null ? (
            <AppealConfidenceDisplay score={uploadResult.appeal_confidence} compact />
          ) : (
            <span className="claim-hero__stat-value">Pending</span>
          )}
        </div>
        <div className="claim-hero__stat">
          <span className="claim-hero__stat-label">Appeal Readiness</span>
          <span className="claim-hero__stat-value">{appealReadiness}</span>
        </div>
        <div className="claim-hero__stat">
          <span className="claim-hero__stat-label">Workflow</span>
          <span className="claim-hero__stat-value claim-hero__stat-value--muted">
            Step {Math.min(stepIndex + 1, STEPS.length)} of {STEPS.length}
          </span>
        </div>
      </div>
    </section>
  );
}
