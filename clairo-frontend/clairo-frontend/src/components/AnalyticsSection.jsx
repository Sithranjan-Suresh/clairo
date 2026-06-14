import { useState } from "react";
import AnalyticsPanel from "./AnalyticsPanel";
import RiskHeatmap from "./RiskHeatmap";

const ANALYTICS_TABS = [
  { id: "riskQueue", label: "Denial Risk Queue" },
  { id: "denialAnalytics", label: "Denial Analytics" },
];

export default function AnalyticsSection({ uploadResult }) {
  const [activeAnalyticsTab, setActiveAnalyticsTab] = useState("riskQueue");

  return (
    <div className="section-stack section-fade analytics-page">
      <header className="analytics-page__header">
        <h1
          className="analytics-page__title"
          style={{ fontFamily: '"DM Serif Display", serif', fontStyle: "italic" }}
        >
          Analytics
        </h1>
        <p className="analytics-page__subtitle font-body">
          Denial risk queue and practice-level denial analytics in one view.
        </p>
      </header>

      <div className="analytics-inner-tabs" role="tablist" aria-label="Analytics views">
        {ANALYTICS_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeAnalyticsTab === tab.id}
            className={`analytics-inner-tabs__tab ${activeAnalyticsTab === tab.id ? "analytics-inner-tabs__tab--active" : ""}`}
            onClick={() => setActiveAnalyticsTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="analytics-inner-panel" role="tabpanel">
        {activeAnalyticsTab === "riskQueue" && (
          <RiskHeatmap uploadResult={uploadResult} />
        )}
        {activeAnalyticsTab === "denialAnalytics" && (
          <AnalyticsPanel />
        )}
      </div>
    </div>
  );
}
