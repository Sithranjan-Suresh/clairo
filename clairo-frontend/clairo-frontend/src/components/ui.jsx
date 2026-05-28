// ─────────────────────────────────────────
// Shared lightweight UI components
// ─────────────────────────────────────────

export function Spinner({ size = 20 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      className="spin"
    >
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  );
}

export function ErrorBox({ message }) {
  if (!message) return null;
  return (
    <div className="error-box">
      <span className="error-icon">⚠</span>
      <span>{message}</span>
    </div>
  );
}

export function Badge({ level }) {
  const map = {
    HIGH: "badge-high",
    MEDIUM: "badge-medium",
    LOW: "badge-low",
    high: "badge-high",
    medium: "badge-medium",
    low: "badge-low",
  };
  return <span className={`badge ${map[level] || "badge-low"}`}>{level ?? "—"}</span>;
}

export function ConfidenceMeter({ score }) {
  const pct = Math.min(100, Math.max(0, score ?? 0));
  const color = pct >= 70 ? "#22c55e" : pct >= 40 ? "#f59e0b" : "#ef4444";
  return (
    <div className="conf-meter">
      <div className="conf-bar-bg">
        <div
          className="conf-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="conf-label" style={{ color }}>
        {pct}%
      </span>
    </div>
  );
}

export function SectionHeader({ icon, title, subtitle }) {
  return (
    <div className="section-header">
      <span className="section-icon">{icon}</span>
      <div>
        <h2 className="section-title">{title}</h2>
        {subtitle && <p className="section-sub">{subtitle}</p>}
      </div>
    </div>
  );
}
