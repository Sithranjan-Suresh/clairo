import {
  formatLabel,
  formatCurrency,
  deriveAppealReadiness,
  deriveRecoverableAmount,
} from "./claimIntakeUtils";

const METRICS = [
  {
    id: "revenue",
    label: "Recoverable Revenue",
    sub: "Estimated denied amount available for appeal",
    getValue: (ur) => deriveRecoverableAmount(ur?.structured_claim),
    getDetail: (ur) => {
      const claim = ur?.structured_claim ?? {};
      return [
        { label: "Billed Amount", value: formatCurrency(claim.billed_amount) },
        { label: "Denied Amount", value: formatCurrency(claim.denied_amount) },
        {
          label: "Recovery explanation",
          value:
            "Recoverable revenue reflects the denied portion eligible for appeal based on extracted financial fields.",
        },
      ];
    },
    variant: (ur) => "default",
  },
  {
    id: "readiness",
    label: "Appeal Readiness",
    sub: "Improves after policy evidence is retrieved",
    getValue: (ur) => deriveAppealReadiness(ur),
    getDetail: (ur) => {
      const missing = [];
      if (!ur?.classification) missing.push("Denial classification");
      const policyDone =
        ur?.policy_retrieved ||
        (ur?.policy_matches_count != null && ur.policy_matches_count > 0);
      if (!policyDone) missing.push("Payer policy evidence");
      if (!ur?.structured_claim?.denial_reason) missing.push("Denial reason documentation");
      return [
        {
          label: "Status",
          value: missing.length
            ? `Pending: ${missing.join(", ")}`
            : "Ready for appeal generation review",
        },
        {
          label: "Next step",
          value: policyDone
            ? "Review documentation checklist, then generate appeal draft."
            : "Retrieve policy evidence to strengthen appeal readiness.",
        },
      ];
    },
    variant: (ur) => {
      const v = deriveAppealReadiness(ur);
      if (v === "High") return "success";
      if (v === "Medium") return "warning";
      if (v === "Low") return "risk";
      return "info";
    },
  },
  {
    id: "policy",
    label: "Policy Matches",
    sub: "Relevant payer policy sources found",
    getValue: (ur) => {
      const count = ur?.policy_matches_count;
      if (count != null) return String(count);
      return ur?.policy_retrieved ? "Retrieved" : "0";
    },
    getDetail: (ur) => {
      const count = ur?.policy_matches_count ?? 0;
      const retrieved = ur?.policy_retrieved || count > 0;
      return [
        {
          label: "Retrieval status",
          value: retrieved
            ? `${count} policy source${count !== 1 ? "s" : ""} on file`
            : "No payer policy evidence retrieved yet",
        },
        {
          label: "Source",
          value: ur?.policy_source ?? "Open Policy Evidence tab to retrieve citations",
        },
      ];
    },
    variant: (ur) => {
      const count = ur?.policy_matches_count ?? 0;
      if (count > 0) return "success";
      return "info";
    },
  },
  {
    id: "risk",
    label: "Denial Risk",
    sub: (ur) =>
      ur?.risk_score != null
        ? `Risk score: ${Math.round(ur.risk_score)}%`
        : "Risk assessment from denial classification",
    getValue: (ur) => formatLabel(ur?.risk_level) || "Pending",
    getDetail: (ur) => [
      { label: "Denial category", value: formatLabel(ur?.classification) },
      {
        label: "Risk score",
        value: ur?.risk_score != null ? `${Math.round(ur.risk_score)}%` : "Not available",
      },
      {
        label: "Denial reason",
        value: ur?.structured_claim?.denial_reason ?? "Not available",
      },
    ],
    variant: (ur) => {
      const risk = String(ur?.risk_level ?? "").toUpperCase();
      if (risk === "HIGH") return "risk";
      if (risk === "MEDIUM") return "warning";
      if (risk === "LOW") return "success";
      return "default";
    },
  },
];

function variantClass(variant) {
  const map = {
    risk: "claim-metric-card--risk",
    warning: "claim-metric-card--warning",
    success: "claim-metric-card--success",
    info: "claim-metric-card--info",
  };
  return map[variant] ?? "";
}

export default function ClaimMetricCards({
  uploadResult,
  expandedMetricCard,
  onToggle,
}) {
  if (!uploadResult) return null;

  return (
    <section className="claim-metrics" aria-label="Claim metrics">
      <div className="claim-metrics__grid">
        {METRICS.map((metric) => {
          const variant = metric.variant(uploadResult);
          const isExpanded = expandedMetricCard === metric.id;
          const sub =
            typeof metric.sub === "function" ? metric.sub(uploadResult) : metric.sub;

          return (
            <div key={metric.id} className="claim-metrics__cell">
              <button
                type="button"
                className={`claim-metric-card glass-panel ${variantClass(variant)} ${isExpanded ? "claim-metric-card--expanded" : ""}`}
                onClick={() =>
                  onToggle(isExpanded ? null : metric.id)
                }
                aria-expanded={isExpanded}
              >
                <span className="claim-metric-card__label">{metric.label}</span>
                <span className="claim-metric-card__value">
                  {metric.getValue(uploadResult)}
                </span>
                <span className="claim-metric-card__sub">{sub}</span>
                <span className="claim-metric-card__hint" aria-hidden="true">
                  {isExpanded ? "▲" : "▼"} Details
                </span>
              </button>

              {isExpanded && (
                <div className="claim-metric-card__detail">
                  {metric.getDetail(uploadResult).map(({ label, value }) => (
                    <div key={label} className="claim-metric-card__detail-row">
                      <span className="claim-metric-card__detail-label">{label}</span>
                      <span className="claim-metric-card__detail-value">{value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
