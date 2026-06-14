import {
  normalizeAppealConfidence,
  getAppealConfidenceStatus,
} from "../utils/appealConfidence";

export default function AppealConfidenceDisplay({ score, compact = false }) {
  const pct = normalizeAppealConfidence(score);
  if (pct == null) {
    return <span className="appeal-confidence appeal-confidence--pending">Pending</span>;
  }

  const { label, tier } = getAppealConfidenceStatus(pct);

  return (
    <div className={`appeal-confidence appeal-confidence--${tier} ${compact ? "appeal-confidence--compact" : ""}`}>
      <div className="appeal-confidence__header">
        <span className="appeal-confidence__value">{pct}%</span>
        <span className={`appeal-confidence__badge appeal-confidence__badge--${tier}`}>
          {label}
        </span>
      </div>
      <div className="appeal-confidence__bar" aria-hidden="true">
        <div
          className="appeal-confidence__bar-fill"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
