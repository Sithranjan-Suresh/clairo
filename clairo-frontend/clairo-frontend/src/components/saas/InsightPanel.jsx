export default function InsightPanel({ uploadResult, appealConfidence }) {
  const claim = uploadResult?.structured_claim ?? {};
  const classification = uploadResult?.classification;

  const missingDocs = claim.documentation_notes
    ? null
    : claim.denial_reason?.toLowerCase().includes("documentation")
      ? "Clinical notes and prior treatment records may be required."
      : "Review payer-specific documentation requirements for this CPT.";

  const policySource = uploadResult?.policy_source
    ?? (uploadResult?.policy_matches_count > 0
      ? `${uploadResult.policy_matches_count} policy match(es) on file`
      : "Run Coverage Evidence after classification");

  const strategy = classification
    ? `Appeal as ${String(classification).replace(/_/g, " ").toLowerCase()} with policy-backed medical necessity.`
    : "Upload and classify a denial to receive a tailored strategy.";

  const viability =
    appealConfidence != null
      ? `${appealConfidence}% confidence`
      : uploadResult?.risk_level
        ? `Risk level: ${uploadResult.risk_level} — score appeals with higher documentation strength.`
        : "Pending viability analysis";

  const items = [
    { label: "Missing documentation", value: missingDocs ?? "None flagged from extraction" },
    { label: "Policy source used", value: policySource },
    { label: "Suggested appeal strategy", value: strategy },
    { label: "Appeal viability", value: viability },
  ];

  return (
    <aside className="insight-panel glass-panel">
      <h3 className="insight-panel__title">Recommended Next Action</h3>
      <ul className="insight-panel__list">
        {items.map(({ label, value }) => (
          <li key={label} className="insight-panel__item">
            <span className="insight-panel__label">{label}</span>
            <p className="insight-panel__value">{value}</p>
          </li>
        ))}
      </ul>
    </aside>
  );
}
