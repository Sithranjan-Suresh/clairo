/**
 * Normalize appeal confidence to an integer 0–100.
 * Accepts fractional (0–1) or percentage (0–100+) inputs.
 */
export function normalizeAppealConfidence(score) {
  if (score == null || score === "") return null;
  const n = Number(score);
  if (Number.isNaN(n)) return null;

  let pct = n > 0 && n <= 1 ? n * 100 : n;
  return Math.min(100, Math.max(0, Math.round(pct)));
}

export function getAppealConfidenceStatus(pct) {
  const value = normalizeAppealConfidence(pct);
  if (value == null) return { label: "Pending", tier: "pending" };
  if (value >= 90) return { label: "Excellent", tier: "excellent" };
  if (value >= 75) return { label: "Strong", tier: "strong" };
  if (value >= 60) return { label: "Moderate", tier: "moderate" };
  if (value >= 40) return { label: "Weak", tier: "weak" };
  return { label: "Poor", tier: "poor" };
}
