import { useState } from "react";
import UploadPanel from "./components/UploadPanel";
import ClaimDetails from "./components/ClaimDetails";
import AppealPanel from "./components/AppealPanel";
import PolicyPanel from "./components/PolicyPanel";
import RiskHeatmap from "./components/RiskHeatmap";
import AnalyticsPanel from "./components/AnalyticsPanel";
import VoicePanel from "./components/VoicePanel";
import PriorAuthPanel from "./components/PriorAuthPanel";

import "./index.css";

const TABS = [
  { id: "upload",    label: "Upload & Extract", icon: "📄" },
  { id: "appeal",    label: "Appeal Letter",    icon: "⚖"  },
  { id: "policy",    label: "Policy Citations", icon: "📚" },
  { id: "heatmap",   label: "Risk Heatmap",     icon: "🌡" },
  { id: "analytics", label: "Analytics",         icon: "📊" },
  { id: "voice", label: "Voice AI", icon: "🎙" },
  { id: "priorauth", label: "Prior Auth Check", icon: "🔐" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("upload");
  const [uploadResult, setUploadResult] = useState(null);

  function handleUploadResult(data) {
    setUploadResult(data);
    // Auto-advance to claim details view
  }

  return (
    <div className="app">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="logo">
          <span className="logo-mark">C</span>
          <div className="logo-text">
            <span className="logo-name">CLAIRO</span>
            <span className="logo-sub">Denial Intelligence</span>
          </div>
        </div>

        <nav className="nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`nav-item ${activeTab === tab.id ? "nav-item--active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="nav-icon">{tab.icon}</span>
              <span className="nav-label">{tab.label}</span>
              {tab.id === "upload" && uploadResult && (
                <span className="nav-dot" title="Claim loaded" />
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="status-dot" />
          <span>Backend: localhost:8000</span>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className="main">
        <div className="content">
          {activeTab === "upload" && (
            <>
              <UploadPanel onResult={handleUploadResult} />
              {uploadResult && <ClaimDetails uploadResult={uploadResult} />}
            </>
          )}
          {activeTab === "appeal"    && <AppealPanel    uploadResult={uploadResult} />}
          {activeTab === "policy"    && <PolicyPanel    uploadResult={uploadResult} />}
          {activeTab === "heatmap"   && <RiskHeatmap    uploadResult={uploadResult} />}
          {activeTab === "analytics" && <AnalyticsPanel />}
          {activeTab === "voice" && <VoicePanel />}
          {activeTab === "priorauth" && <PriorAuthPanel uploadResult={uploadResult} />}
        </div>
      </main>
    </div>
  );
}
