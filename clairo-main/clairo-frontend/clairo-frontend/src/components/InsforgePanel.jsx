import { useState, useEffect, useCallback } from "react";
import { Database, Zap, RefreshCw, Bot, ChevronRight, Activity } from "lucide-react";
import { API_BASE_URL } from "../api";

// ── helpers ────────────────────────────────────────────────────────────────

async function apiFetch(path, opts = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, opts);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function RiskBadge({ level }) {
  const map = {
    HIGH:   { color: "var(--color-high)",   bg: "var(--glow-high)" },
    MEDIUM: { color: "var(--color-medium)", bg: "var(--glow-medium)" },
    LOW:    { color: "var(--color-low)",    bg: "var(--glow-low)" },
  };
  const style = map[level] ?? map.LOW;
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: "0.06em",
      padding: "2px 7px", borderRadius: 6,
      color: style.color, background: style.bg, border: `1px solid ${style.color}33`,
    }}>
      {level}
    </span>
  );
}

function StatCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius: 12, padding: "16px 20px", flex: 1, minWidth: 120,
    }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: color ?? "var(--text)", fontVariantNumeric: "tabular-nums" }}>
        {value ?? "—"}
      </div>
      <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{label}</div>
      {sub && <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2, opacity: 0.7 }}>{sub}</div>}
    </div>
  );
}

// ── main component ─────────────────────────────────────────────────────────

const PAYERS = ["", "UHC", "Aetna", "BCBS", "Cigna", "Humana"];

export default function InsforgePanel() {
  const [status, setStatus]         = useState(null);
  const [claims, setClaims]         = useState([]);
  const [loadingStatus, setLS]      = useState(false);
  const [loadingClaims, setLC]      = useState(false);
  const [agentQuery, setAgentQuery] = useState("");
  const [agentPayer, setAgentPayer] = useState("");
  const [agentResult, setAgentRes]  = useState(null);
  const [agentLoading, setAL]       = useState(false);
  const [agentError, setAE]         = useState(null);
  const [claimsError, setCE]        = useState(null);

  const loadStatus = useCallback(async () => {
    setLS(true);
    try { setStatus(await apiFetch("/insforge/status")); }
    catch (e) { console.error(e); }
    finally { setLS(false); }
  }, []);

  const loadClaims = useCallback(async () => {
    setLC(true); setCE(null);
    try { const d = await apiFetch("/insforge/live-claims?limit=15"); setClaims(d.claims ?? []); }
    catch (e) { setCE(e.message); }
    finally { setLC(false); }
  }, []);

  useEffect(() => { loadStatus(); loadClaims(); }, [loadStatus, loadClaims]);

  async function runAgent() {
    if (!agentQuery.trim()) return;
    setAL(true); setAE(null); setAgentRes(null);
    try {
      const body = { query: agentQuery };
      if (agentPayer) body.payer = agentPayer;
      const d = await apiFetch("/insforge/agent-run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setAgentRes(d);
    } catch (e) { setAE(e.message); }
    finally { setAL(false); }
  }

  const stats = status?.live_stats;
  const isInsforge = status?.insforge_connected;

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "32px 24px", fontFamily: "inherit" }}>

      {/* ── Header ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: "linear-gradient(135deg, #2563eb22, #6366f122)",
          border: "1px solid #6366f144",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Database size={18} color="#6366f1" />
        </div>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text)" }}>
            InsForge Live Database
          </h2>
          <p style={{ margin: 0, fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
            Real-time claim feed from InsForge Postgres — the agent-native backend powering CLAIRO
          </p>
        </div>
        <button
          onClick={() => { loadStatus(); loadClaims(); }}
          style={{
            marginLeft: "auto", background: "var(--surface2)", border: "1px solid var(--border)",
            borderRadius: 8, padding: "6px 12px", color: "var(--text-muted)", cursor: "pointer",
            display: "flex", alignItems: "center", gap: 6, fontSize: 12,
          }}
        >
          <RefreshCw size={12} className={loadingStatus || loadingClaims ? "spin" : ""} />
          Refresh
        </button>
      </div>

      {/* ── DB Status Banner ── */}
      <div style={{
        background: isInsforge ? "rgba(99,102,241,0.08)" : "rgba(245,158,11,0.08)",
        border: `1px solid ${isInsforge ? "#6366f144" : "#f59e0b44"}`,
        borderRadius: 12, padding: "12px 16px", marginBottom: 24,
        display: "flex", alignItems: "center", gap: 10,
      }}>
        <Activity size={14} color={isInsforge ? "#6366f1" : "#f59e0b"} />
        <span style={{ fontSize: 12, fontWeight: 600, color: isInsforge ? "#818cf8" : "#fbbf24" }}>
          {status ? status.backend : "Connecting…"}
        </span>
        {status?.query_latency_ms != null && (
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 4 }}>
            · {status.query_latency_ms}ms query latency
          </span>
        )}
        {!isInsforge && status && (
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 4 }}>
            · Set INSFORGE_DATABASE_URL in .env to connect InsForge Postgres
          </span>
        )}
        {status?.status === "healthy" && (
          <span style={{
            marginLeft: "auto", fontSize: 10, fontWeight: 700,
            color: "var(--color-low)", background: "var(--glow-low)",
            padding: "2px 8px", borderRadius: 6,
          }}>HEALTHY</span>
        )}
      </div>

      {/* ── Live Stats ── */}
      <div style={{ display: "flex", gap: 12, marginBottom: 28, flexWrap: "wrap" }}>
        <StatCard label="Total Claims" value={stats?.total_claims ?? "—"} />
        <StatCard label="High Risk" value={stats?.high_risk_claims ?? "—"} color="var(--color-high)" />
        <StatCard label="Appeals Generated" value={stats?.appeals_generated ?? "—"} color="var(--color-low)" />
        <StatCard label="Appeal Rate" value={stats ? `${stats.appeal_rate_pct}%` : "—"} color="var(--color-info)" />
      </div>

      {/* ── Agent Query ── */}
      <div style={{
        background: "var(--surface)", border: "1px solid var(--border)",
        borderRadius: 14, padding: "20px 20px", marginBottom: 28,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <Bot size={15} color="#6366f1" />
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
            InsForge Agent Query
          </span>
          <span style={{
            fontSize: 10, color: "#818cf8", background: "rgba(99,102,241,0.12)",
            border: "1px solid #6366f133", borderRadius: 6, padding: "1px 7px", marginLeft: 4,
          }}>LIVE DB</span>
        </div>
        <p style={{ margin: "0 0 12px", fontSize: 12, color: "var(--text-muted)" }}>
          Ask the autonomous agent a question. It queries InsForge Postgres for live context,
          then synthesizes denial intelligence using CLAIRO's AI layer.
        </p>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input
            value={agentQuery}
            onChange={e => setAgentQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && runAgent()}
            placeholder="e.g. What are the highest-risk UHC claims? How many appeals have been filed?"
            style={{
              flex: 1, background: "var(--surface2)", border: "1px solid var(--border)",
              borderRadius: 8, padding: "9px 12px", color: "var(--text)", fontSize: 13,
              outline: "none",
            }}
          />
          <select
            value={agentPayer}
            onChange={e => setAgentPayer(e.target.value)}
            style={{
              background: "var(--surface2)", border: "1px solid var(--border)",
              borderRadius: 8, padding: "9px 12px", color: "var(--text)", fontSize: 12,
              cursor: "pointer",
            }}
          >
            {PAYERS.map(p => <option key={p} value={p}>{p || "All Payers"}</option>)}
          </select>
          <button
            onClick={runAgent}
            disabled={agentLoading || !agentQuery.trim()}
            style={{
              background: agentLoading ? "var(--surface2)" : "#4f46e5",
              border: "none", borderRadius: 8, padding: "9px 18px",
              color: "white", fontSize: 13, fontWeight: 600, cursor: agentLoading ? "default" : "pointer",
              display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap",
            }}
          >
            {agentLoading ? (
              <>
                <RefreshCw size={13} className="spin" /> Running…
              </>
            ) : (
              <>Run Agent <ChevronRight size={13} /></>
            )}
          </button>
        </div>
        {/* Quick prompts */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {[
            "What are the highest-risk claims in the database?",
            "How many appeals have been generated so far?",
            "Which payer has the most denials?",
          ].map(q => (
            <button key={q} onClick={() => setAgentQuery(q)} style={{
              fontSize: 11, color: "var(--text-muted)", background: "var(--surface2)",
              border: "1px solid var(--border)", borderRadius: 6, padding: "3px 10px",
              cursor: "pointer",
            }}>{q}</button>
          ))}
        </div>

        {agentError && (
          <div style={{ marginTop: 14, color: "var(--color-high)", fontSize: 12 }}>
            Error: {agentError}
          </div>
        )}

        {agentResult && (
          <div style={{ marginTop: 16, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
            <div style={{ fontSize: 11, color: "#818cf8", marginBottom: 10, fontWeight: 600, letterSpacing: "0.05em" }}>
              AGENT RESPONSE · {agentResult.agent_response?.data_source ?? "InsForge Postgres"}
            </div>
            <p style={{ margin: "0 0 12px", fontSize: 13, color: "var(--text)", lineHeight: 1.6 }}>
              {agentResult.agent_response?.summary}
            </p>
            {agentResult.agent_response?.key_findings?.length > 0 && (
              <ul style={{ margin: "0 0 12px", paddingLeft: 18 }}>
                {agentResult.agent_response.key_findings.map((f, i) => (
                  <li key={i} style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4, lineHeight: 1.5 }}>
                    {f}
                  </li>
                ))}
              </ul>
            )}
            {agentResult.agent_response?.recommendation && (
              <div style={{
                background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.25)",
                borderRadius: 8, padding: "10px 14px", fontSize: 12, color: "#6ee7b7",
              }}>
                <strong style={{ color: "var(--color-low)" }}>Recommendation: </strong>
                {agentResult.agent_response.recommendation}
              </div>
            )}
            <div style={{ marginTop: 10, fontSize: 11, color: "var(--text-muted)" }}>
              Context: {agentResult.insforge_context?.total_claims} total claims ·{" "}
              {agentResult.insforge_context?.high_risk_claims_sampled} high-risk sampled
              {agentResult.insforge_context?.payer_stats && (
                <> · {agentResult.insforge_context.payer_stats.payer}: {agentResult.insforge_context.payer_stats.total_denials} denials, avg risk {agentResult.insforge_context.payer_stats.avg_risk_score}</>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Live Claim Feed ── */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <Zap size={14} color="#f59e0b" />
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
            Live Claim Feed
          </span>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            · {claims.length} most recent records from InsForge Postgres
          </span>
        </div>

        {claimsError && (
          <div style={{ color: "var(--color-high)", fontSize: 12, marginBottom: 12 }}>
            {claimsError}
          </div>
        )}

        {loadingClaims && !claims.length ? (
          <div style={{ color: "var(--text-muted)", fontSize: 13, padding: "20px 0" }}>
            Querying InsForge Postgres…
          </div>
        ) : claims.length === 0 ? (
          <div style={{
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 12, padding: "32px 24px", textAlign: "center",
          }}>
            <Database size={28} color="var(--text-muted)" style={{ marginBottom: 10, opacity: 0.4 }} />
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13 }}>
              No claims in database yet.
            </p>
            <p style={{ margin: "6px 0 0", color: "var(--text-muted)", fontSize: 12, opacity: 0.7 }}>
              Upload a denial PDF on the CLΔIRO tab, or go to Analytics → Seed Demo Data.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["ID", "Payer", "Patient", "CPT", "Classification", "Risk", "Appeal", "Date"].map(h => (
                    <th key={h} style={{
                      textAlign: "left", padding: "8px 10px",
                      color: "var(--text-muted)", fontWeight: 600,
                      fontSize: 11, letterSpacing: "0.05em", whiteSpace: "nowrap",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {claims.map((c, i) => (
                  <tr key={c.id} style={{
                    borderBottom: "1px solid var(--border)",
                    background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)",
                  }}>
                    <td style={{ padding: "9px 10px", color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                      #{c.id}
                    </td>
                    <td style={{ padding: "9px 10px", color: "var(--text)", fontWeight: 500 }}>{c.payer}</td>
                    <td style={{ padding: "9px 10px", color: "var(--text-muted)" }}>{c.patient_id}</td>
                    <td style={{ padding: "9px 10px", color: "var(--text-muted)", fontFamily: "monospace" }}>{c.cpt_codes}</td>
                    <td style={{ padding: "9px 10px", color: "var(--text-muted)" }}>
                      {(c.classification ?? "—").replace(/_/g, " ")}
                    </td>
                    <td style={{ padding: "9px 10px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <RiskBadge level={c.risk_level} />
                        <span style={{ fontSize: 11, color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                          {c.risk_score != null ? Math.round(c.risk_score) : "—"}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: "9px 10px" }}>
                      <span style={{
                        fontSize: 10, fontWeight: 600,
                        color: c.appeal_generated ? "var(--color-low)" : "var(--text-muted)",
                      }}>
                        {c.appeal_generated ? "✓ Yes" : "No"}
                      </span>
                    </td>
                    <td style={{ padding: "9px 10px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                      {c.created_at}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spin { animation: spin 0.8s linear infinite; }
      `}</style>
    </div>
  );
}
