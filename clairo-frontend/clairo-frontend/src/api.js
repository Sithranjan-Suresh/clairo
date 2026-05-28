// ─────────────────────────────────────────
// CLAIRO — Central API Configuration
// Change API_BASE_URL here to point at any backend
// ─────────────────────────────────────────

export const API_BASE_URL = "http://localhost:8000";

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
  const res = await fetch(`${API_BASE_URL}/analytics/seed`, { method: "POST" });
  if (!res.ok) throw new Error(`Seed failed: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function exportAppealPDF(structured_claim, classification, appeal_letter, confidence_score) {
  const res = await fetch(`${API_BASE_URL}/export/export-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      appeal_letter,
      structured_claim,
      confidence_score,
      classification,
    }),
  });
  if (!res.ok) throw new Error(`PDF export failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "appeal_letter.pdf";
  a.click();
  URL.revokeObjectURL(url);
}

export async function processVoice(audioFile) {
  const formData = new FormData();
  formData.append("file", audioFile);
  const res = await fetch(`${API_BASE_URL}/voice/process`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Voice processing failed: ${res.status}`);
  return res.json();
}