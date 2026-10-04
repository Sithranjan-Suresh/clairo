import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { getPolicies, searchPolicies } from "../api";
import { ErrorBox, SectionHeader, Spinner } from "./ui";
import "./dashboard.css";

export default function PolicyLibrary() {
  const [policies, setPolicies] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState(null);

  useEffect(() => {
    getPolicies().then(setPolicies).catch((e) => setError(e.message));
  }, []);

  const grouped = useMemo(() => {
    const map = new Map();
    (policies ?? []).forEach((p) => {
      const key = p.payer.toUpperCase();
      map.set(key, [...(map.get(key) ?? []), p]);
    });
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [policies]);

  async function onSearch(e) {
    e.preventDefault();
    if (query.trim().length < 3) return;
    setSearching(true); setError(null);
    try { setResults((await searchPolicies(query.trim())).results); }
    catch (err) { setError(err.message); }
    finally { setSearching(false); }
  }

  return (
    <div className="panel panel--section dash">
      <SectionHeader
        icon="📚" title="Policy library"
        subtitle={policies ? `${policies.length} payer policy documents indexed for retrieval` : "Indexed payer policy documents"}
      />
      <form className="dash__filters" onSubmit={onSearch}>
        <label className="dash__search">
          <Search size={14} aria-hidden="true" />
          <input
            value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="Search policies, e.g. “conservative treatment before knee arthroscopy”"
            aria-label="Search policies"
          />
        </label>
        <button className="btn-primary" disabled={searching || query.trim().length < 3}>
          {searching ? <Spinner size={14} /> : "Search"}
        </button>
      </form>
      <ErrorBox message={error} />

      {results && (
        <div className="policy-results">
          <h4 className="detail__h">Top matches</h4>
          {results.length === 0 && <p className="detail__muted">No matches.</p>}
          {results.map((r, i) => (
            <article key={i} className="policy-hit">
              <header><strong>{r.source}</strong> <span className="demo-tag">{r.payer}</span></header>
              <p>{r.text}</p>
            </article>
          ))}
        </div>
      )}

      {!policies && !error && <div className="dash__empty"><Spinner size={18} /> Loading…</div>}
      <div className="policy-groups">
        {grouped.map(([payer, docs]) => (
          <section key={payer} className="policy-group">
            <h4 className="detail__h">{payer} <span className="detail__muted">({docs.length})</span></h4>
            <ul>
              {docs.map((d) => (
                <li key={d.id}><span>{d.title}</span><span className="detail__muted">{d.chunk_count} chunks</span></li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
