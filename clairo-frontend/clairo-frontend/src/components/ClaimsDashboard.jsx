import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowDown, ArrowUp, RefreshCw, Search, X } from "lucide-react";
import {
  generateAppeal, getClaim, getClaimAudit, listClaims, reanalyzeClaim,
} from "../api";
import { useAuth } from "../auth/AuthContext";
import { Badge, ConfidenceMeter, ErrorBox, SectionHeader, Spinner } from "./ui";
import "./dashboard.css";

const PAGE_SIZE = 10;

export function parseTs(value) {
  if (!value) return null;
  const s = String(value);
  return new Date(/[zZ]$|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`);
}
export const fmtTs = (value) => parseTs(value)?.toLocaleString() ?? "—";

export function StatusPill({ status }) {
  return <span className={`status-pill status-pill--${status}`}>{status}</span>;
}

const ACTION_LABELS = {
  "claim.created": "Claim uploaded",
  "claim.analyzed": "Analysis completed",
  "claim.analysis_failed": "Analysis failed",
  "claim.reanalysis_requested": "Re-analysis requested",
  "appeal.requested": "Appeal requested",
  "appeal.generated": "Appeal letter generated",
};
export const actionLabel = (a) => ACTION_LABELS[a] ?? a;

export default function ClaimsDashboard({ onLoadClaim }) {
  const [filters, setFilters] = useState({ q: "", status: "", risk: "", sort_by: "id", order: "desc" });
  const [debouncedQ, setDebouncedQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const requestSeq = useRef(0);

  useEffect(() => {
    const t = setTimeout(() => { setDebouncedQ(filters.q); setOffset(0); }, 300);
    return () => clearTimeout(t);
  }, [filters.q]);

  const load = useCallback(async ({ silent = false } = {}) => {
    const seq = ++requestSeq.current;
    if (!silent) setLoading(true);
    try {
      const data = await listClaims({
        q: debouncedQ, status: filters.status, risk: filters.risk,
        sort_by: filters.sort_by, order: filters.order, limit: PAGE_SIZE, offset,
      });
      if (seq === requestSeq.current) { setPage(data); setError(null); }
    } catch (e) {
      if (seq === requestSeq.current) setError(e.message);
    } finally {
      if (seq === requestSeq.current) setLoading(false);
    }
  }, [debouncedQ, filters.status, filters.risk, filters.sort_by, filters.order, offset]);

  useEffect(() => { load(); }, [load]);

  // Claims still being analysed by the background worker: keep refreshing.
  const hasPending = page.items.some((c) => c.status === "analyzing");
  useEffect(() => {
    if (!hasPending) return undefined;
    const t = setInterval(() => load({ silent: true }), 3000);
    return () => clearInterval(t);
  }, [hasPending, load]);

  const setFilter = (key, value) => { setFilters((f) => ({ ...f, [key]: value })); setOffset(0); };
  const toggleSort = (col) => {
    setFilters((f) => ({ ...f, sort_by: col, order: f.sort_by === col && f.order === "desc" ? "asc" : "desc" }));
    setOffset(0);
  };
  const sortIcon = (col) => filters.sort_by !== col ? null
    : filters.order === "desc" ? <ArrowDown size={12} /> : <ArrowUp size={12} />;

  const pages = Math.max(1, Math.ceil(page.total / PAGE_SIZE));
  const current = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="panel panel--section dash">
      <div className="dash__head">
        <SectionHeader icon="🗂" title="Claims" subtitle="Every denial you've uploaded, plus shared demo data" />
        <button className="btn-secondary" onClick={() => load()} disabled={loading}>
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh
        </button>
      </div>

      <div className="dash__filters">
        <label className="dash__search">
          <Search size={14} aria-hidden="true" />
          <input
            value={filters.q} onChange={(e) => setFilter("q", e.target.value)}
            placeholder="Search payer, patient, CPT, reason…" aria-label="Search claims"
          />
        </label>
        <select value={filters.status} onChange={(e) => setFilter("status", e.target.value)} aria-label="Status">
          <option value="">All statuses</option>
          {["analyzing", "analyzed", "appealed", "failed"].map((s) => <option key={s}>{s}</option>)}
        </select>
        <select value={filters.risk} onChange={(e) => setFilter("risk", e.target.value)} aria-label="Risk level">
          <option value="">All risk levels</option>
          <option value="HIGH">High risk</option>
          <option value="MEDIUM">Medium risk</option>
          <option value="LOW">Low risk</option>
        </select>
      </div>

      <ErrorBox message={error} />

      <div className="dash__table-wrap">
        <table className="dash__table">
          <thead>
            <tr>
              <th><button onClick={() => toggleSort("id")}># {sortIcon("id")}</button></th>
              <th><button onClick={() => toggleSort("payer")}>Payer {sortIcon("payer")}</button></th>
              <th>CPT</th>
              <th>Denial type</th>
              <th><button onClick={() => toggleSort("risk_score")}>Risk {sortIcon("risk_score")}</button></th>
              <th><button onClick={() => toggleSort("status")}>Status {sortIcon("status")}</button></th>
              <th>Appeal</th>
            </tr>
          </thead>
          <tbody>
            {loading && page.items.length === 0 && (
              <tr><td colSpan={7} className="dash__empty"><Spinner size={18} /> Loading claims…</td></tr>
            )}
            {!loading && page.items.length === 0 && (
              <tr><td colSpan={7} className="dash__empty">
                No claims match. Upload a denial from the CLΔIRO tab to create one.
              </td></tr>
            )}
            {page.items.map((c) => (
              <tr
                key={c.id} tabIndex={0}
                className={selectedId === c.id ? "is-selected" : ""}
                onClick={() => setSelectedId(c.id)}
                onKeyDown={(e) => e.key === "Enter" && setSelectedId(c.id)}
              >
                <td>{c.id}{c.is_demo && <span className="demo-tag">demo</span>}</td>
                <td>{c.payer ?? "—"}</td>
                <td>{c.cpt_codes.join(", ") || "—"}</td>
                <td>{c.classification?.replace(/_/g, " ") ?? "—"}</td>
                <td>{c.risk_score != null ? <><Badge level={c.risk_level} /> {Math.round(c.risk_score)}</> : "—"}</td>
                <td><StatusPill status={c.status} /></td>
                <td>{c.appeal_generated ? "✓" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="dash__pager">
        <span>{page.total} claim{page.total === 1 ? "" : "s"}</span>
        <div>
          <button className="btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Previous</button>
          <span className="dash__pageno">Page {current} of {pages}</span>
          <button className="btn-secondary" disabled={current >= pages} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</button>
        </div>
      </div>

      {selectedId && createPortal(
        <ClaimDetail
          key={selectedId} claimId={selectedId}
          onClose={() => setSelectedId(null)}
          onLoadClaim={onLoadClaim}
          onChanged={() => load({ silent: true })}
        />,
        // Portal: ancestors with backdrop-filter would otherwise become the
        // containing block for this position:fixed drawer.
        document.body,
      )}
    </div>
  );
}

function ClaimDetail({ claimId, onClose, onLoadClaim, onChanged }) {
  const { user, isAdmin } = useAuth();
  const [claim, setClaim] = useState(null);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [c, a] = await Promise.all([getClaim(claimId), getClaimAudit(claimId)]);
      setClaim(c); setAudit(a); setError(null);
    } catch (e) { setError(e.message); }
  }, [claimId]);

  useEffect(() => { refresh(); }, [refresh]);

  const canModify = claim && (isAdmin || claim.owner_id === user?.id);
  const latestAppeal = claim?.appeals?.[0];

  async function run(kind, fn) {
    setBusy(kind); setError(null);
    try { await fn(); await refresh(); onChanged(); }
    catch (e) { setError(e.message); await refresh(); }
    finally { setBusy(null); }
  }

  return (
    <aside className="detail glass-panel" aria-label="Claim details">
      <div className="detail__head">
        <h3 className="font-ui">Claim #{claimId}</h3>
        <button className="detail__close" onClick={onClose} aria-label="Close details"><X size={16} /></button>
      </div>
      <ErrorBox message={error} />
      {!claim ? <div className="dash__empty"><Spinner size={18} /> Loading…</div> : (
        <>
          <div className="detail__meta">
            <StatusPill status={claim.status} />
            {claim.is_demo && <span className="demo-tag">shared demo data</span>}
          </div>
          {claim.error_message && <ErrorBox message={claim.error_message} />}

          <dl className="detail__grid">
            {[
              ["Payer", claim.payer], ["Patient", claim.patient_id],
              ["CPT codes", claim.cpt_codes.join(", ")],
              ["Denial type", claim.classification?.replace(/_/g, " ")],
              ["Billed", claim.billed_amount], ["Denied", claim.denied_amount],
              ["Service date", claim.service_date], ["Reason", claim.denial_reason],
            ].map(([k, v]) => (
              <div key={k}><dt>{k}</dt><dd>{v || "—"}</dd></div>
            ))}
          </dl>

          <h4 className="detail__h">Risk</h4>
          {claim.risk_score != null ? (
            <>
              <ConfidenceMeter score={Math.round(claim.risk_score)} />
              {claim.risk_history[0] && (
                <>
                  <ul className="detail__flags">
                    {(claim.risk_history[0].flags ?? []).map((f) => <li key={f}>{f}</li>)}
                  </ul>
                  <p className="detail__note">{claim.risk_history[0].remediation}</p>
                  <p className="detail__muted">
                    Rules {claim.risk_history[0].rule_score}/60 · AI documentation review {claim.risk_history[0].llm_score}/40
                    {claim.risk_history.length > 1 && ` · ${claim.risk_history.length} scoring runs`}
                  </p>
                </>
              )}
            </>
          ) : <p className="detail__muted">Not scored yet.</p>}

          <h4 className="detail__h">Appeal &amp; policy evidence</h4>
          {latestAppeal ? (
            <>
              <p className="detail__muted">Confidence {latestAppeal.confidence_score}% · {fmtTs(latestAppeal.created_at)}</p>
              <pre className="detail__letter">{latestAppeal.letter_text}</pre>
              {(latestAppeal.citations ?? []).length > 0 && (
                <ul className="detail__cites">
                  {latestAppeal.citations.map((c, i) => (
                    <li key={i}><strong>{c.source}</strong> — {String(c.text).slice(0, 220)}…</li>
                  ))}
                </ul>
              )}
            </>
          ) : <p className="detail__muted">No appeal drafted yet.</p>}

          <div className="btn-row detail__actions">
            {claim.classification && (
              <button className="btn-primary" disabled={!canModify || busy || claim.status === "analyzing"}
                title={canModify ? "" : "Demo data is read-only"}
                onClick={() => run("appeal", () => generateAppeal(null, null, claim.id))}>
                {busy === "appeal" ? <Spinner size={14} /> : latestAppeal ? "Regenerate appeal" : "Generate appeal"}
              </button>
            )}
            {(claim.status === "failed" || claim.status === "analyzed") && (
              <button className="btn-secondary" disabled={!canModify || busy}
                onClick={() => run("analyze", () => reanalyzeClaim(claim.id))}>
                {busy === "analyze" ? <Spinner size={14} /> : "Re-analyze"}
              </button>
            )}
            {claim.classification && onLoadClaim && (
              <button className="btn-secondary" onClick={() => onLoadClaim(claim)}>Open in appeal workspace</button>
            )}
          </div>

          <h4 className="detail__h">Audit history</h4>
          <ol className="timeline">
            {audit.map((a) => (
              <li key={a.id}>
                <span className="timeline__what">{actionLabel(a.action)}</span>
                <span className="timeline__who">{a.actor_email ?? "system"}</span>
                <span className="timeline__when">{fmtTs(a.created_at)}</span>
              </li>
            ))}
            {audit.length === 0 && <li className="detail__muted">No recorded events.</li>}
          </ol>
        </>
      )}
    </aside>
  );
}
