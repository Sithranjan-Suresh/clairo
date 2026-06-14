// ─────────────────────────────────────────
// CLAIRO — Central API Configuration
// Change API_BASE_URL here to point at any backend
// ─────────────────────────────────────────

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// Upload a denial PDF — returns structured claim + classification + risk
export async function uploadDenial(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
  return res.json();
}

// Generate an appeal letter from a structured claim + classification
export async function generateAppeal(structured_claim, classification) {
  const res = await fetch(`${API_BASE_URL}/appeal/generate-from-claim`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ structured_claim, classification }),
  });
  if (!res.ok) throw new Error(`Appeal generation failed: ${res.status} ${res.statusText}`);
  return res.json();
}

// Score a single claim for denial risk
export async function scoreClaim(cpt_codes, payer, documentation_notes) {
  const res = await fetch(`${API_BASE_URL}/risk/score-claim`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cpt_codes, payer, documentation_notes }),
  });
  if (!res.ok) throw new Error(`Risk scoring failed: ${res.status} ${res.statusText}`);
  return res.json();
}

// Score a queue of claims for the heatmap
export async function scoreQueue(claims) {
  const res = await fetch(`${API_BASE_URL}/risk/score-queue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ claims }),
  });
  if (!res.ok) throw new Error(`Queue scoring failed: ${res.status} ${res.statusText}`);
  return res.json();
}

// Retrieve policy citations for a denial
export async function retrievePolicy(payer, cpt, denial_reason, classification = "") {
  const params = new URLSearchParams({ payer, cpt, denial_reason, classification });
  const res = await fetch(`${API_BASE_URL}/rag/retrieve?${params}`);
  if (!res.ok) throw new Error(`Policy retrieval failed: ${res.status} ${res.statusText}`);
  return res.json();
}

// Get appeal viability rating
export async function getViability(confidence_score, classification, payer) {
  const res = await fetch(`${API_BASE_URL}/export/viability`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confidence_score, classification, payer }),
  });
  if (!res.ok) throw new Error(`Viability check failed: ${res.status} ${res.statusText}`);
  return res.json();
}

// Get analytics summary stats
export async function getAnalyticsSummary() {
  const res = await fetch(`${API_BASE_URL}/analytics/summary`);
  if (!res.ok) throw new Error(`Analytics failed: ${res.status} ${res.statusText}`);
  return res.json();
}

// Seed demo data
export async function seedDemoData() {
  const res = await fetch(`${API_BASE_URL}/analytics/seed?force=true`, { method: "POST" });
  if (!res.ok) throw new Error(`Seed failed: ${res.status} ${res.statusText}`);
  return res.json();
}

// Analytics breakdowns
export async function getAnalyticsByPayer() {
  const res = await fetch(`${API_BASE_URL}/analytics/by-payer`);
  if (!res.ok) throw new Error(`Analytics by payer failed: ${res.status}`);
  return res.json();
}

export async function getAnalyticsByClassification() {
  const res = await fetch(`${API_BASE_URL}/analytics/by-classification`);
  if (!res.ok) throw new Error(`Analytics by classification failed: ${res.status}`);
  return res.json();
}

export async function getAnalyticsByCpt() {
  const res = await fetch(`${API_BASE_URL}/analytics/by-cpt`);
  if (!res.ok) throw new Error(`Analytics by CPT failed: ${res.status}`);
  return res.json();
}

export async function getAnalyticsMonthlyTrend() {
  const res = await fetch(`${API_BASE_URL}/analytics/by-month`);
  if (!res.ok) throw new Error(`Monthly trend failed: ${res.status}`);
  return res.json();
}

// Export appeal as PDF (backend); returns blob on success
export async function exportAppealPdf({ appeal_letter, structured_claim, classification, confidence_score = 0 }) {
  const res = await fetch(`${API_BASE_URL}/export/export-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ appeal_letter, structured_claim, confidence_score: Math.round(confidence_score ?? 0), classification }),
  });
  if (!res.ok) {
    const err = new Error(`PDF export failed: ${res.status} ${res.statusText}`);
    err.status = res.status;
    throw err;
  }
  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return res.json();
  }
  const blob = await res.blob();
  return { blob, filename: "clairo-appeal-letter.pdf" };
}

// Process voice/audio note for structured denial insights
export async function processVoiceAudio(file, claimContext = null) {
  const formData = new FormData();
  formData.append("file", file);
  if (claimContext) {
    formData.append(
      "claim_context",
      typeof claimContext === "string" ? claimContext : JSON.stringify(claimContext),
    );
  }
  const res = await fetch(`${API_BASE_URL}/voice/process`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`Voice processing failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Check prior authorization requirements for a procedure
export async function checkPriorAuthorization(payload) {
  const res = await fetch(`${API_BASE_URL}/api/prior-auth-check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Prior auth check failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Build prior authorization packet from uploaded clinical documents
export async function checkPriorAuthorizationDocuments(formData) {
  const url = `${API_BASE_URL}/api/prior-auth-check-documents`;

  if (import.meta.env.DEV) {
    console.info("[Prior Auth] POST", url);
  }

  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (import.meta.env.DEV) {
    console.info("[Prior Auth] response status", res.status);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((item) => item.msg || item.message || JSON.stringify(item))
          .join("; ");
      } else if (body.message) {
        detail = body.message;
      }
    } catch {
      /* ignore */
    }

    if (res.status === 404) {
      throw new Error(
        "Prior Authorization endpoint not found. Check that backend route /api/prior-auth-check-documents is registered.",
      );
    }
    if (res.status === 422) {
      throw new Error(detail || "Invalid request. Check payer, CPT code, and uploaded files.");
    }
    if (res.status >= 500) {
      throw new Error(detail || "Prior auth service error. Check backend logs.");
    }
    throw new Error(
      typeof detail === "string" ? detail : "Prior auth packet generation failed.",
    );
  }

  const data = await res.json();
  if (import.meta.env.DEV) {
    console.info("[Prior Auth] packet received", data?.packet ? "ok" : "missing packet");
  }
  if (!data?.packet) {
    throw new Error("Invalid response from prior auth service.");
  }
  return data;
}

/** Client-side PDF fallback when backend export is unavailable */
export function printAppealLetterPdf(letter, meta = {}) {
  const formatted = (letter ?? "").replace(/\\n/g, "\n");
  const win = window.open("", "_blank", "noopener,noreferrer");
  if (!win) {
    throw new Error("Pop-up blocked. Allow pop-ups to export the appeal letter.");
  }
  const payer = meta.payer ?? "—";
  const patient = meta.patient_id ?? "—";
  win.document.write(`<!DOCTYPE html><html><head><title>Appeal Letter</title>
<style>
  body { font-family: Georgia, serif; color: #111; padding: 48px; max-width: 720px; margin: 0 auto; line-height: 1.6; }
  h1 { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
  .meta { font-size: 12px; color: #555; margin-bottom: 24px; }
  pre { white-space: pre-wrap; font-family: inherit; font-size: 13px; }
</style></head><body>
<h1>Insurance Appeal Letter</h1>
<p class="meta">Payer: ${payer} · Patient: ${patient}</p>
<pre>${formatted.replace(/</g, "&lt;")}</pre>
</body></html>`);
  win.document.close();
  win.focus();
  win.print();
}

// ── InsForge endpoints ────────────────────────────────────────────

export async function getInsforgeStatus() {
  const res = await fetch(`${API_BASE_URL}/insforge/status`);
  if (!res.ok) throw new Error(`InsForge status failed: ${res.status}`);
  return res.json();
}

export async function getInsforgeLiveClaims(limit = 20) {
  const res = await fetch(`${API_BASE_URL}/insforge/live-claims?limit=${limit}`);
  if (!res.ok) throw new Error(`InsForge live claims failed: ${res.status}`);
  return res.json();
}

export async function runInsforgeAgent(query, payer = null, cpt_codes = null) {
  const body = { query };
  if (payer) body.payer = payer;
  if (cpt_codes) body.cpt_codes = cpt_codes;
  const res = await fetch(`${API_BASE_URL}/insforge/agent-run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`InsForge agent run failed: ${res.status}`);
  return res.json();
}
