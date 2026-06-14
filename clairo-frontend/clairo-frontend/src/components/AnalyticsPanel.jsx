import { useState } from "react";
import {
  getAnalyticsSummary,
  getAnalyticsByPayer,
  getAnalyticsByClassification,
  getAnalyticsByCpt,
  getAnalyticsMonthlyTrend,
  seedDemoData,
} from "../api";
import { Spinner, ErrorBox, SectionHeader } from "./ui";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const CHART_FILLS = ["#4F7CFF", "#18C29C", "#7A5AF8", "#F5B942", "#E05D5D", "#4F7CFF"];
const CHART_LINE = "#4F7CFF";
const CHART_GRID = "rgba(255, 255, 255, 0.08)";

function mapRows(rows, nameKey, countKey = "count") {
  if (!Array.isArray(rows)) return [];
  return rows.map((r) => ({
    name: (r[nameKey] ?? "Unknown").toString().replace(/_/g, " "),
    count: r[countKey] ?? r.denial_count ?? 0,
  }));
}

function mapTrend(rows) {
  if (!Array.isArray(rows)) return [];
  return rows.map((r) => ({
    name: r.month ?? r.period ?? r.label ?? "—",
    count: r.count ?? r.denial_count ?? r.denials ?? 0,
  }));
}

export default function AnalyticsPanel() {
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [byPayer, setByPayer] = useState([]);
  const [byClass, setByClass] = useState([]);
  const [byCpt, setByCpt] = useState([]);
  const [monthlyTrend, setMonthlyTrend] = useState([]);

  async function handleLoad() {
    setError(null);
    setLoading(true);
    try {
      const summaryData = await getAnalyticsSummary();
      setSummary(summaryData);

      const [payerRes, classRes, cptRes, trendRes] = await Promise.allSettled([
        getAnalyticsByPayer(),
        getAnalyticsByClassification(),
        getAnalyticsByCpt(),
        getAnalyticsMonthlyTrend(),
      ]);

      setByPayer(payerRes.status === "fulfilled" ? payerRes.value : []);
      setByClass(classRes.status === "fulfilled" ? classRes.value : []);
      setByCpt(cptRes.status === "fulfilled" ? cptRes.value : []);
      setMonthlyTrend(trendRes.status === "fulfilled" ? trendRes.value : []);
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

  const payerData = mapRows(byPayer, "payer", "denial_count");
  const classData = mapRows(byClass, "classification");
  const cptData = mapRows(byCpt, "cpt_code").length
    ? mapRows(byCpt, "cpt_code")
    : mapRows(byCpt, "cpt");
  const trendData = mapTrend(monthlyTrend);

  const hasCharts =
    payerData.length > 0 ||
    classData.length > 0 ||
    cptData.length > 0 ||
    trendData.length > 0;

  return (
    <div className="panel analytics-dashboard">
      <SectionHeader
        icon="📊"
        title="Denial Analytics"
        subtitle="Practice-level denial trends and payer benchmarks"
      />

      <div className="btn-row">
        <button className="btn-primary" onClick={handleLoad} disabled={loading}>
          {loading ? (
            <>
              <Spinner size={16} /> Loading…
            </>
          ) : (
            "Load Analytics"
          )}
        </button>
        <button className="btn-secondary" onClick={handleSeed} disabled={seeding}>
          {seeding ? (
            <>
              <Spinner size={16} /> Seeding…
            </>
          ) : (
            "Seed Demo Data"
          )}
        </button>
      </div>

      <ErrorBox message={error} />

      {summary && (
        <>
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
              <span className="stat-num">{summary.benchmark_gap ?? "N/A"}</span>
              <span className="stat-label">Benchmark Gap</span>
            </div>
            <div className="analytics-stat">
              <span className="stat-num">{summary.excess_annual_loss ?? "N/A"}</span>
              <span className="stat-label">Est. Excess Loss</span>
            </div>
          </div>

          {hasCharts ? (
            <div className="analytics-charts-grid">
              {payerData.length > 0 && (
                <div className="chart-card">
                  <h3 className="chart-title">Denials by Payer</h3>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={payerData} margin={{ top: 0, right: 8, left: -16, bottom: 0 }}>
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#a3a3a3" }} />
                      <YAxis tick={{ fontSize: 11, fill: "#a3a3a3" }} stroke={CHART_GRID} />
                      <Tooltip />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {payerData.map((_, idx) => (
                          <Cell key={idx} fill={CHART_FILLS[idx % CHART_FILLS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {classData.length > 0 && (
                <div className="chart-card">
                  <h3 className="chart-title">Denials by Classification</h3>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={classData} margin={{ top: 0, right: 8, left: -16, bottom: 0 }}>
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#a3a3a3" }} interval={0} angle={-12} textAnchor="end" height={48} />
                      <YAxis tick={{ fontSize: 11, fill: "#a3a3a3" }} stroke={CHART_GRID} />
                      <Tooltip />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {classData.map((_, idx) => (
                          <Cell key={idx} fill={CHART_FILLS[(idx + 1) % CHART_FILLS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {cptData.length > 0 && (
                <div className="chart-card">
                  <h3 className="chart-title">Denials by CPT Code</h3>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={cptData} margin={{ top: 0, right: 8, left: -16, bottom: 0 }}>
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#a3a3a3" }} />
                      <YAxis tick={{ fontSize: 11, fill: "#a3a3a3" }} stroke={CHART_GRID} />
                      <Tooltip />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {cptData.map((_, idx) => (
                          <Cell key={idx} fill={CHART_FILLS[(idx + 2) % CHART_FILLS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {trendData.length > 0 && (
                <div className="chart-card chart-card--wide">
                  <h3 className="chart-title">Monthly Denial Trend</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={trendData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#a3a3a3" }} />
                      <YAxis tick={{ fontSize: 11, fill: "#a3a3a3" }} stroke={CHART_GRID} />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="count"
                        stroke={CHART_LINE}
                        strokeWidth={2}
                        dot={{ fill: "#18C29C", r: 3 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          ) : (
            <p className="analytics-empty-hint">
              Seed demo data to populate payer, classification, CPT, and trend charts.
            </p>
          )}
        </>
      )}
    </div>
  );
}
