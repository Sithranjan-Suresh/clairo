// ─────────────────────────────────────────
// CLAIRO — API client
// Every request goes through authFetch, which attaches the JWT and signals the
// app to log out when the server says the session is no longer valid.
// ─────────────────────────────────────────

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "clairo_token";
export const UNAUTHORIZED_EVENT = "clairo:unauthorized";

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(token) {
  try { localStorage.setItem(TOKEN_KEY, token); } catch { /* storage unavailable */ }
}
export function clearToken() {
  try { localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ }
}

export async function authFetch(path, opts = {}) {
  const headers = new Headers(opts.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE_URL}${path}`, { ...opts, headers });
  // A 401 on /auth/login just means "wrong password" — only treat it as an
  // expired session on authenticated endpoints.
  if (res.status === 401 && !path.startsWith("/auth/login") && !path.startsWith("/auth/register")) {
    clearToken();
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  return res;
}

/** Best human-readable message from a FastAPI/our-API error response. */
async function errorMessage(res, fallback) {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((d) => (d.msg || d.message || JSON.stringify(d)).replace(/^Value error, /, ""))
        .join("; ");
    }
    if (typeof body.error === "string") return body.error;
    if (typeof body.message === "string") return body.message;
  } catch { /* non-JSON body */ }
  if (res.status === 429) return "Too many requests — please wait a moment and try again.";
  if (res.status === 401) return "Your session has expired. Please sign in again.";
  return `${fallback} (${res.status})`;
}

async function request(path, opts, fallback) {
  let res;
  try {
    res = await authFetch(path, opts);
  } catch {
    throw new Error("Can't reach the server. If it was idle it may be waking up — try again in a few seconds.");
  }
  if (!res.ok) throw new Error(await errorMessage(res, fallback));
  return res;
}

const json = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

// ── auth ─────────────────────────────────────────────────────────
export async function register(email, password) {
  const res = await request("/auth/register", json({ email, password }), "Registration failed");
  return res.json();
}
export async function login(email, password) {
  const res = await request("/auth/login", json({ email, password }), "Sign in failed");
  return res.json();
}
export async function getMe() {
  return (await request("/auth/me", {}, "Session check failed")).json();
}

// ── background jobs ──────────────────────────────────────────────
export async function waitForJob(jobId, { timeoutMs = 180000, intervalMs = 1200 } = {}) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const job = await (await request(`/jobs/${jobId}`, {}, "Job status check failed")).json();
    if (job.status === "succeeded") return job;
    if (job.status === "failed") throw new Error(job.error || "Processing failed.");
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("This is taking longer than expected. Check the Claims tab for the result.");
}

// ── claims ───────────────────────────────────────────────────────
export async function getClaim(id) {
  return (await request(`/claims/${id}`, {}, "Could not load claim")).json();
}

export async function listClaims(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  });
  return (await request(`/claims?${qs}`, {}, "Could not load claims")).json();
}

export async function getClaimAudit(id) {
  return (await request(`/claims/${id}/audit`, {}, "Could not load audit history")).json();
}

export async function reanalyzeClaim(id) {
  const { job_id } = await (await request(`/claims/${id}/analyze`, { method: "POST" }, "Could not start analysis")).json();
  await waitForJob(job_id);
  return getClaim(id);
}

/** Shape a stored claim like the old synchronous upload response so the
 *  existing intake/appeal panels keep working unchanged. */
export function claimToWorkspace(claim) {
  return {
    claim_id: claim.id,
    filename: claim.documents?.[0]?.original_filename ?? `Claim #${claim.id}`,
    structured_claim: {
      payer: claim.payer,
      patient_id: claim.patient_id,
      cpt_codes: claim.cpt_codes ?? [],
      denial_reason: claim.denial_reason,
      billed_amount: claim.billed_amount,
      denied_amount: claim.denied_amount,
      service_date: claim.service_date,
    },
    classification: claim.classification,
    risk_score: claim.risk_score,
    risk_level: claim.risk_level,
  };
}

// Upload a denial PDF. Analysis happens in a background worker; we poll the job.
export async function uploadDenial(file, { onStatus } = {}) {
  const formData = new FormData();
  formData.append("file", file);
  const created = await (await request("/claims", { method: "POST", body: formData }, "Upload failed")).json();
  onStatus?.("analyzing");
  await waitForJob(created.job_id);
  return claimToWorkspace(await getClaim(created.claim_id));
}

// Generate an appeal letter. With a claim id it is persisted (and audited) and
// runs as a background job; without one it falls back to the stateless endpoint.
export async function generateAppeal(structured_claim, classification, claimId = null) {
  if (claimId) {
    const { job_id } = await (await request(`/claims/${claimId}/appeal`, { method: "POST" }, "Appeal generation failed")).json();
    await waitForJob(job_id);
    const claim = await getClaim(claimId);
    const appeal = claim.appeals?.[0];
    return {
      appeal_letter: appeal?.letter_text ?? "",
      confidence_score: appeal?.confidence_score ?? 0,
      confidence_rationale: appeal?.confidence_rationale,
      citations: appeal?.citations ?? [],
    };
  }
  return (await request("/appeal/generate-from-claim", json({ structured_claim, classification }), "Appeal generation failed")).json();
}

// ── stateless scoring / retrieval ───────────────────────────────
export async function scoreClaim(cpt_codes, payer, documentation_notes) {
  return (await request("/risk/score-claim", json({ cpt_codes, payer, documentation_notes }), "Risk scoring failed")).json();
}

export async function scoreQueue(claims) {
  return (await request("/risk/score-queue", json({ claims }), "Queue scoring failed")).json();
}

export async function retrievePolicy(payer, cpt, denial_reason, classification = "") {
  const params = new URLSearchParams({ payer, cpt, denial_reason, classification });
  return (await request(`/rag/retrieve?${params}`, {}, "Policy retrieval failed")).json();
}

export async function getViability(confidence_score, classification, payer) {
  return (await request("/export/viability", json({ confidence_score, classification, payer }), "Viability check failed")).json();
}

// ── policy library / audit ──────────────────────────────────────
export async function getPolicies() {
  return (await request("/policies", {}, "Could not load policies")).json();
}

export async function searchPolicies(q, payer = "") {
  const params = new URLSearchParams({ q });
  if (payer) params.set("payer", payer);
  return (await request(`/policies/search?${params}`, {}, "Policy search failed")).json();
}

export async function getAuditLogs(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  });
  return (await request(`/audit-logs?${qs}`, {}, "Could not load audit log")).json();
}

// ── analytics ───────────────────────────────────────────────────
export async function getAnalyticsSummary() {
  return (await request("/analytics/summary", {}, "Analytics failed")).json();
}

// Admin only: reseeds the shared demo claims (real users' claims are untouched).
export async function seedDemoData() {
  return (await request("/analytics/seed?force=true", { method: "POST" }, "Seed failed")).json();
}

export async function getAnalyticsByPayer() {
  return (await request("/analytics/by-payer", {}, "Analytics by payer failed")).json();
}
export async function getAnalyticsByClassification() {
  return (await request("/analytics/by-classification", {}, "Analytics by classification failed")).json();
}
export async function getAnalyticsByCpt() {
  return (await request("/analytics/by-cpt", {}, "Analytics by CPT failed")).json();
}
export async function getAnalyticsMonthlyTrend() {
  return (await request("/analytics/by-month", {}, "Monthly trend failed")).json();
}

// ── export / voice / prior auth ─────────────────────────────────
// Export appeal as PDF (backend); returns blob on success
export async function exportAppealPdf({ appeal_letter, structured_claim, classification, confidence_score = 0 }) {
  const res = await request(
    "/export/export-pdf",
    json({ appeal_letter, structured_claim, confidence_score: Math.round(confidence_score ?? 0), classification }),
    "PDF export failed",
  );
  if ((res.headers.get("content-type") ?? "").includes("application/json")) return res.json();
  return { blob: await res.blob(), filename: "clairo-appeal-letter.pdf" };
}

export async function processVoiceAudio(file, claimContext = null) {
  const formData = new FormData();
  formData.append("file", file);
  if (claimContext) {
    formData.append("claim_context", typeof claimContext === "string" ? claimContext : JSON.stringify(claimContext));
  }
  return (await request("/voice/process", { method: "POST", body: formData }, "Voice processing failed")).json();
}

export async function checkPriorAuthorization(payload) {
  return (await request("/api/prior-auth-check", json(payload), "Prior auth check failed")).json();
}

// Build prior authorization packet from uploaded clinical documents
export async function checkPriorAuthorizationDocuments(formData) {
  const data = await (await request("/api/prior-auth-check-documents", { method: "POST", body: formData }, "Prior auth packet generation failed")).json();
  if (!data?.packet) throw new Error("Invalid response from prior auth service.");
  return data;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]
  ));
}

/** Client-side PDF fallback when backend export is unavailable */
export function printAppealLetterPdf(letter, meta = {}) {
  const formatted = (letter ?? "").replace(/\\n/g, "\n");
  const win = window.open("", "_blank", "noopener,noreferrer");
  if (!win) {
    throw new Error("Pop-up blocked. Allow pop-ups to export the appeal letter.");
  }
  // structured_claim fields are LLM-extracted from an uploaded PDF, i.e.
  // attacker-controlled input — never interpolate them into this HTML
  // document unescaped.
  const payer = escapeHtml(meta.payer ?? "—");
  const patient = escapeHtml(meta.patient_id ?? "—");
  win.document.write(`<!DOCTYPE html><html><head><title>Appeal Letter</title>
<style>
  body { font-family: Georgia, serif; color: #111; padding: 48px; max-width: 720px; margin: 0 auto; line-height: 1.6; }
  h1 { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
  .meta { font-size: 12px; color: #555; margin-bottom: 24px; }
  pre { white-space: pre-wrap; font-family: inherit; font-size: 13px; }
</style></head><body>
<h1>Insurance Appeal Letter</h1>
<p class="meta">Payer: ${payer} · Patient: ${patient}</p>
<pre>${escapeHtml(formatted)}</pre>
</body></html>`);
  win.document.close();
  win.focus();
  win.print();
}

// ── InsForge ────────────────────────────────────────────────────
export async function getInsforgeStatus() {
  return (await request("/insforge/status", {}, "InsForge status failed")).json();
}
export async function getInsforgeLiveClaims(limit = 20) {
  return (await request(`/insforge/live-claims?limit=${limit}`, {}, "InsForge live claims failed")).json();
}
export async function runInsforgeAgent(query, payer = null, cpt_codes = null) {
  const body = { query };
  if (payer) body.payer = payer;
  if (cpt_codes) body.cpt_codes = cpt_codes;
  return (await request("/insforge/agent-run", json(body), "InsForge agent run failed")).json();
}
