import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { getAuditLogs } from "../api";
import { ErrorBox, SectionHeader, Spinner } from "./ui";
import { actionLabel, fmtTs } from "./ClaimsDashboard";
import "./dashboard.css";

const PAGE_SIZE = 20;
const ACTIONS = [
  "auth.register", "auth.login", "auth.login_failed", "claim.created", "claim.analyzed",
  "claim.analysis_failed", "appeal.requested", "appeal.generated", "admin.seed_demo_data",
];

export default function AuditLogPanel() {
  const [action, setAction] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await getAuditLogs({ action, limit: PAGE_SIZE, offset }));
      setError(null);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [action, offset]);

  useEffect(() => { load(); }, [load]);

  const pages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const current = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="panel panel--section dash">
      <div className="dash__head">
        <SectionHeader icon="🛡" title="Audit log" subtitle="Administrator view of every recorded action" />
        <button className="btn-secondary" onClick={load} disabled={loading}>
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh
        </button>
      </div>
      <div className="dash__filters">
        <select value={action} onChange={(e) => { setAction(e.target.value); setOffset(0); }} aria-label="Action">
          <option value="">All actions</option>
          {ACTIONS.map((a) => <option key={a} value={a}>{actionLabel(a)} ({a})</option>)}
        </select>
      </div>
      <ErrorBox message={error} />
      <div className="dash__table-wrap">
        <table className="dash__table dash__table--static">
          <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Entity</th><th>IP</th></tr></thead>
          <tbody>
            {loading && data.items.length === 0 && (
              <tr><td colSpan={5} className="dash__empty"><Spinner size={18} /></td></tr>
            )}
            {data.items.map((a) => (
              <tr key={a.id}>
                <td>{fmtTs(a.created_at)}</td>
                <td>{a.actor_email ?? "system"}</td>
                <td>{actionLabel(a.action)}</td>
                <td>{a.entity_type ? `${a.entity_type} #${a.entity_id}` : "—"}</td>
                <td>{a.ip_address ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="dash__pager">
        <span>{data.total} events</span>
        <div>
          <button className="btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Previous</button>
          <span className="dash__pageno">Page {current} of {pages}</span>
          <button className="btn-secondary" disabled={current >= pages} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</button>
        </div>
      </div>
    </div>
  );
}
