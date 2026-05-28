import { useState } from "react";
import { getAnalyticsSummary, seedDemoData } from "../api";
import { API_BASE_URL } from "../api";
import { Spinner, ErrorBox, SectionHeader } from "./ui";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const COLORS = ["#3b82f6", "#f59e0b", "#22c55e", "#ef4444", "#a855f7", "#06b6d4"];

export default function AnalyticsPanel() {
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [byPayer, setByPayer] = useState([]);
  const [byClass, setByClass] = useState([]);
  const [byMonth, setByMonth] = useState([]);
  const [byCpt, setByCpt] = useState([]);

  async function handleLoad() {
    setError(null);
    setLoading(true);
    try {
      const [summaryData, payerRes, classRes, monthRes, cptRes] = await Promise.all([
        getAnalyticsSummary(),
        fetch(`${API_BASE_URL}/analytics/by-payer`).then((r) => r.json()),
        fetch(`${API_BASE_URL}/analytics/by-classification`).then((r) => r.json()),
        fetch(`${API_BASE_URL}/analytics/by-month`).then((r) => r.json()),
        fetch(`${API_BASE_URL}/analytics/by-cpt`).then((r) => r.json()),
      ]);
      setSummary(summaryData);
      setByPayer(payerRes);
      setByClass(classRes);
      setByMonth(monthRes);
      setByCpt(cptRes);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSeed() {
    setError(null);
    setSeeding(true);
    try {
      await seedDemoData();
      await handleLoad();
    } catch (e) {
      setError(e.message);
    } finally {
      setSeeding(false);
    }
  }

  const payerData = byPayer.map((r) => ({ name: r.payer, count: r.denial_count }));
  const classData = byClass.map((r) => ({
    name: (r.classification ?? "").replace(/_/g, " "),
    count: r.count,
  }));
  const monthData = byMonth.map((r) => ({ name: r.month, count: r.count }));
  const cptData = byCpt.map((r) => ({ name: r.cpt_code, count: r.denial_count }));

  return (
    <div className="panel">
      <SectionHeader
        icon="📊"
        title="Denial Pattern Analytics"
        subtitle="Practice-level denial trends and payer benchmarks"
      />

      <div className="btn-row">
        <button className="btn-primary" onClick={handleLoad} disabled={loading}>
          {loading ? <><Spinner size={16} /> Loading…</> : "Load Analytics"}
        </button>
        <button className="btn-secondary" onClick={handleSeed} disabled={seeding}>
          {seeding ? <><Spinner size={16} /> Seeding…</> : "Seed Demo Data"}
        </button>
      </div>

      <ErrorBox message={error} />

      {summary && (
        <>
          {/* Summary stats */}
          <div className="analytics-stats">
            <div className="analytics-stat">
              <span className="stat-num">{summary.total_denials_processed ?? 0}</span>
              <span className="stat-label">Total Denials</span>
            </div>
            <div className="analytics-stat">
              <span className="stat-num">{summary.appeals_generated ?? 0}</span>
              <span className="stat-label">Appeals Generated</span>
            </div>
            <div className="analytics-stat">
              <span className="stat-num">
                {summary.avg_risk_score != null ? summary.avg_risk_score : "N/A"}
              </span>
              <span className="stat-label">Avg Risk Score</span>
            </div>
            <div className="analytics-stat">
              <span className="stat-num">{summary.total_denied_revenue ?? "N/A"}</span>
              <span className="stat-label">Total Denied Revenue</span>
            </div>
          </div>

          {/* Benchmark row */}
          <div className="analytics-stats">
            <div className="analytics-stat">
              <span className="stat-num">{summary.practice_denial_rate ?? "N/A"}</span>
              <span className="stat-label">Practice Denial Rate</span>
            </div>
            <div className="analytics-stat">
              <span className="stat-num">{summary.industry_denial_rate ?? "N/A"}</span>
              <span className="stat-label">Industry Avg</span>
            </div>
            <div className="analytics-stat">
              <span className="stat-num" style={{ color: "#ef4444" }}>
                {summary.benchmark_gap ?? "N/A"}
              </span>
              <span className="stat-label">Benchmark Gap</span>
            </div>
            <div className="analytics-stat">
              <span className="stat-num">{summary.excess_annual_loss ?? "N/A"}</span>
              <span className="stat-label">Est. Excess Loss</span>
            </div>
          </div>

          {/* Denials by Payer */}
          {payerData.length > 0 && (
            <div className="chart-section">
              <h3 className="chart-title">Denials by Payer</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={payerData} margin={{ top: 0, right: 8, left: -16, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {payerData.map((_, idx) => (
                      <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Denials by Category */}
          {classData.length > 0 && (
            <div className="chart-section">
              <h3 className="chart-title">Denials by Category</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={classData} margin={{ top: 0, right: 8, left: -16, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {classData.map((_, idx) => (
                      <Cell key={idx} fill={COLORS[(idx + 2) % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Denials by Month */}
          {monthData.length > 0 && (
            <div className="chart-section">
              <h3 className="chart-title">Monthly Denial Trend</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={monthData} margin={{ top: 0, right: 8, left: -16, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {monthData.map((_, idx) => (
                      <Cell key={idx} fill={COLORS[(idx + 1) % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Denials by CPT */}
          {cptData.length > 0 && (
            <div className="chart-section">
              <h3 className="chart-title">Denials by CPT Code</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={cptData} margin={{ top: 0, right: 8, left: -16, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {cptData.map((_, idx) => (
                      <Cell key={idx} fill={COLORS[(idx + 3) % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}