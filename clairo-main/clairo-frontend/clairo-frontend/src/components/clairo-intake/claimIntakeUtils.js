import { deriveWorkflowIndex } from "../saas/WorkflowStepper";
import { normalizeAppealConfidence } from "../../utils/appealConfidence";

const WORKFLOW_STEPS = [
  "Upload",
  "Extract",
  "Classify",
  "Retrieve Policy",
  "Generate Appeal",
  "Export",
];

export function formatLabel(value) {
  if (value == null || value === "") return "Not available";
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatCurrency(raw) {
  if (raw == null || raw === "") return "Not available";
  const str = String(raw).replace(/[$,]/g, "").trim();
  const num = Number(str);
  if (Number.isNaN(num)) return String(raw).startsWith("$") ? raw : `$${raw}`;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatCptCodes(cpt) {
  if (cpt == null) return "Not available";
  if (Array.isArray(cpt)) return cpt.join(", ") || "Not available";
  return String(cpt) || "Not available";
}

export function displayValue(value) {
  if (value == null || value === "" || value === "N/A") return "Not available";
  return value;
}

export function getWorkflowStage(uploadResult) {
  const index = deriveWorkflowIndex(uploadResult);
  if (index >= WORKFLOW_STEPS.length) return "Complete";
  return WORKFLOW_STEPS[index];
}

export function deriveAppealReadiness(uploadResult) {
  if (!uploadResult?.classification) return "Pending";
  const normalized = normalizeAppealConfidence(uploadResult.appeal_confidence);
  if (normalized != null) {
    if (normalized >= 75) return "High";
    if (normalized >= 60) return "Medium";
    return "Low";
  }
  const policyDone =
    uploadResult.policy_retrieved ||
    (uploadResult.policy_matches_count != null && uploadResult.policy_matches_count > 0);
  if (policyDone && uploadResult.risk_level === "LOW") return "High";
  if (policyDone) return "Medium";
  const risk = String(uploadResult.risk_level ?? "").toUpperCase();
  if (risk === "HIGH") return "Low";
  if (risk === "MEDIUM") return "Medium";
  return "Pending";
}

export function deriveRecommendationStatus(uploadResult) {
  if (!uploadResult?.classification) return "Pending analysis";
  const policyDone =
    uploadResult.policy_retrieved ||
    (uploadResult.policy_matches_count != null && uploadResult.policy_matches_count > 0);
  if (!policyDone) return "Pending policy evidence";
  const risk = String(uploadResult.risk_level ?? "").toUpperCase();
  const denial = uploadResult.structured_claim?.denial_reason?.toLowerCase() ?? "";
  if (denial.includes("documentation") || denial.includes("not sufficiently documented")) {
    return "Needs documentation";
  }
  if (risk === "LOW" || risk === "MEDIUM") return "Strong candidate for appeal";
  return "Needs documentation";
}

export function deriveRecoverableAmount(claim) {
  return formatCurrency(claim?.denied_amount ?? claim?.billed_amount);
}

export function deriveMissingDocumentation(claim) {
  const reason = claim?.denial_reason?.toLowerCase() ?? "";
  if (claim?.documentation_notes) return claim.documentation_notes;
  if (reason.includes("documentation") || reason.includes("conservative")) {
    return "Prior conservative treatment records, physician notes, imaging reports, therapy records, and clinical justification.";
  }
  const cpt = formatCptCodes(claim?.cpt_codes);
  return `Review payer-specific documentation requirements for CPT ${cpt !== "Not available" ? cpt : "this procedure"}.`;
}

export function deriveSuggestedStrategy(classification) {
  if (!classification) return "Upload and classify a denial to receive a tailored strategy.";
  return `Appeal as ${formatLabel(classification).toLowerCase()} with policy-backed evidence.`;
}

export function deriveAppealViabilityText(uploadResult, appealViability) {
  if (appealViability?.viability) {
    const score = appealViability.viability_score != null
      ? ` Score: ${Math.round(appealViability.viability_score)}%.`
      : "";
    return `${formatLabel(appealViability.viability)} viability.${score}`;
  }
  if (uploadResult?.appeal_confidence != null) {
    const normalized = normalizeAppealConfidence(uploadResult.appeal_confidence);
    return `${normalized}% confidence — viability improves with stronger documentation.`;
  }
  const risk = uploadResult?.risk_level;
  if (risk) {
    return `${formatLabel(risk)} risk. Score improves with stronger documentation and payer policy support.`;
  }
  return "Pending viability analysis after policy retrieval.";
}

export const DOCUMENTATION_ITEMS = [
  { id: "denial_letter", label: "Denial letter / EOB", defaultStatus: "Available" },
  { id: "clinical_notes", label: "Clinical notes", defaultStatus: "Missing" },
  { id: "auth_records", label: "Authorization records", defaultStatus: "Recommended" },
  { id: "conservative_treatment", label: "Prior conservative treatment history", defaultStatus: "Missing" },
  { id: "imaging", label: "Imaging reports", defaultStatus: "Recommended" },
  { id: "medical_necessity", label: "Physician medical necessity statement", defaultStatus: "Recommended" },
];

export function deriveDocumentationStrength(uploadResult) {
  const reason = uploadResult?.structured_claim?.denial_reason?.toLowerCase() ?? "";
  if (reason.includes("documentation") || reason.includes("conservative")) {
    return { level: "Medium", note: "Appeal can improve with more clinical support." };
  }
  if (uploadResult?.policy_matches_count > 0) {
    return { level: "Good", note: "Policy evidence retrieved — add clinical notes to strengthen." };
  }
  return { level: "Developing", note: "Complete documentation review before generating appeal." };
}
