import { CheckCircle2, Circle, AlertCircle } from "lucide-react";
import {
  formatLabel,
  deriveRecommendationStatus,
  deriveMissingDocumentation,
  deriveSuggestedStrategy,
  deriveAppealViabilityText,
} from "./claimIntakeUtils";

function StatusIcon({ type }) {
  if (type === "complete") return <CheckCircle2 size={14} className="ai-rec__icon ai-rec__icon--ok" />;
  if (type === "alert") return <AlertCircle size={14} className="ai-rec__icon ai-rec__icon--warn" />;
  return <Circle size={14} className="ai-rec__icon ai-rec__icon--muted" />;
}

export default function AIAppealRecommendation({ uploadResult, appealViability }) {
  if (!uploadResult) return null;

  const claim = uploadResult.structured_claim ?? {};
  const status = deriveRecommendationStatus(uploadResult);
  const denialReason =
    claim.denial_reason ??
    "Medical necessity criteria not met. Prior conservative treatments were not sufficiently documented.";
  const cpt = Array.isArray(claim.cpt_codes)
    ? claim.cpt_codes[0]
    : claim.cpt_codes ?? "this procedure";
  const nextAction = `Review payer-specific documentation requirements for CPT ${cpt}.`;
  const missingDocs = deriveMissingDocumentation(claim);
  const strategy = deriveSuggestedStrategy(uploadResult.classification);
  const viability = deriveAppealViabilityText(uploadResult, appealViability);

  const sections = [
    { title: "Why this claim was denied", value: denialReason, icon: "alert" },
    { title: "Recommended next action", value: nextAction, icon: "pending" },
    { title: "Missing documentation", value: missingDocs, icon: "alert" },
    { title: "Suggested appeal strategy", value: strategy, icon: "complete" },
    { title: "Appeal viability", value: viability, icon: "pending" },
  ];

  return (
    <section className="ai-recommendation glass-panel" aria-label="AI appeal recommendation">
      <div className="ai-recommendation__header">
        <h2 className="ai-recommendation__title">AI Appeal Recommendation</h2>
        <span className="ai-recommendation__status">{status}</span>
      </div>

      <ul className="ai-recommendation__sections">
        {sections.map(({ title, value, icon }) => (
          <li key={title} className="ai-recommendation__section">
            <div className="ai-recommendation__section-head">
              <StatusIcon type={icon} />
              <span className="ai-recommendation__section-title">{title}</span>
            </div>
            <p className="ai-recommendation__section-body">{value}</p>
          </li>
        ))}
      </ul>

      {uploadResult.classification && (
        <p className="ai-recommendation__footer">
          Classification: <strong>{formatLabel(uploadResult.classification)}</strong>
        </p>
      )}
    </section>
  );
}
