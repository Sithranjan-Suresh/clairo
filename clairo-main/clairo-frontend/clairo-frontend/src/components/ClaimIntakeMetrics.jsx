import MetricCard from "./saas/MetricCard";

function formatAmount(claim) {
  const raw = claim?.denied_amount ?? claim?.billed_amount;
  if (raw == null || raw === "") return null;
  const str = String(raw);
  return str.startsWith("$") ? str : `$${str}`;
}

export default function ClaimIntakeMetrics({ uploadResult }) {
  if (!uploadResult) return null;

  const claim = uploadResult.structured_claim ?? {};
  const riskLabel = uploadResult.risk_level
    ? String(uploadResult.risk_level)
    : uploadResult.risk_score != null
      ? `${uploadResult.risk_score}%`
      : null;

  const policyCount = uploadResult.policy_matches_count;
  const appealConf =
    uploadResult.appeal_confidence != null
      ? `${uploadResult.appeal_confidence}%`
      : null;

  const status = uploadResult.classification
    ? String(uploadResult.classification).replace(/_/g, " ")
    : "Pending";

  return (
    <div className="claim-intake__metrics">
      <span className="claim-intake__metrics-title">Claim summary</span>
      <div className="metrics-grid">
        <MetricCard label="Claim Status" value={status} />
        <MetricCard
          label="Denial Risk"
          value={riskLabel ?? "Pending"}
          variant={
            String(uploadResult.risk_level ?? "").toUpperCase() === "HIGH"
              ? "risk"
              : "default"
          }
        />
        <MetricCard label="Appeal Confidence" value={appealConf ?? "Pending"} />
        <MetricCard
          label="Policy Matches Found"
          value={
            policyCount != null
              ? String(policyCount)
              : "Not available"
          }
        />
        <MetricCard
          label="Est. Recoverable Amount"
          value={formatAmount(claim) ?? "Not available"}
        />
      </div>
    </div>
  );
}
