export default function MetricCard({ label, value, variant = "default", sub }) {
  // Auto-detect color from value if it looks like a risk level or percentage
  function resolveVariant() {
    if (variant === "risk") return "risk";
    if (variant === "success") return "success";
    if (variant === "info") return "info";
    if (typeof value === "string") {
      const v = value.toUpperCase();
      if (v === "HIGH") return "risk";
      if (v === "MEDIUM") return "warning";
      if (v === "LOW") return "success";
      // If it's a percentage, color by magnitude
      const pct = parseFloat(value);
      if (!isNaN(pct) && value.includes("%")) {
        if (pct >= 70) return "success";
        if (pct >= 40) return "warning";
        if (pct > 0)   return "risk";
      }
    }
    return "default";
  }

  const resolved = resolveVariant();

  const valueColorMap = {
    risk:    "#fca5a5",
    warning: "#fcd34d",
    success: "#6ee7b7",
    info:    "#a5b4fc",
    default: "#ffffff",
  };

  const cardClassMap = {
    risk:    "metric-card--risk",
    warning: "metric-card--warning",
    success: "metric-card--success",
    info:    "metric-card--info",
    default: "",
  };

  return (
    <div className={`metric-card ${cardClassMap[resolved]}`}>
      <span className="metric-card__label">{label}</span>
      <span
        className="metric-card__value"
        style={{ color: valueColorMap[resolved] }}
      >
        {value ?? "—"}
      </span>
      {sub && <span className="metric-card__sub">{sub}</span>}
    </div>
  );
}
