import { motion, LayoutGroup } from "framer-motion";
import { BeamsBackground } from "@/components/ui/beams-background";
import TopDockNav from "./TopDockNav";
import ClairoAISection from "./ClairoAISection";
import AppealLetterSection from "./AppealLetterSection";
import AnalyticsSection from "./AnalyticsSection";
import PriorAuthSection from "./PriorAuthSection";
import InsforgePanel from "./InsforgePanel";
import ClaimsDashboard from "./ClaimsDashboard";
import PolicyLibrary from "./PolicyLibrary";
import AuditLogPanel from "./AuditLogPanel";
import UserMenu from "./UserMenu";
import { BrandMark } from "./BrandMark";
import ClairoLogo from "./ClairoLogo";
import { API_BASE_URL } from "../api";

const revealEase = [0.4, 0, 0.2, 1];

export default function ClairoExperience({
  activeTab,
  setActiveTab,
  uploadResult,
  onUploadResult,
  onUpdateClaim,
  onPolicyRetrieved,
  appealData,
  appealViability,
  appealLetterText,
  onAppealGenerated,
  onAppealLetterChange,
  onExportCompleted,
  onResetAppeal,
  onLoadClaim,
}) {
  const goToIntake = () => setActiveTab("Clairo.AI");
  // Clicking "Explore" used to run a multi-phase shader/collapse/reveal
  // intro before landing on the app. Removed — the app now renders
  // immediately, no animation.
  const settled = true;
  const revealing = true;
  const showHeaderDelta = true;

  const dashboardShell = (
    <div
      className={`app ${settled ? "app--settled" : "app--intro"} ${revealing || settled ? "app--with-beams" : ""} ${settled && activeTab === "Clairo.AI" ? "app--clairo-page" : ""}`}
    >
      <div
        className={`app-shell app-shell--content ${revealing ? "app-shell--revealed" : "app-shell--prepared"}`}
      >
        <UserMenu />
        <header className="app-top app-layer">
          {showHeaderDelta && (
            <div className="app-top__delta-wrap">
              <motion.span
                layoutId="clairo-delta"
                className="app-header__delta"
                transition={{ duration: 0.55, ease: revealEase }}
              >
                <ClairoLogo inline className="app-header__logo" />
              </motion.span>
            </div>
          )}

          <div
            className={`intro-reveal-target ${revealing ? "intro-reveal-target--visible" : ""}`}
            style={{ transitionDelay: "0ms" }}
          >
            <TopDockNav
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              hasClaim={!!uploadResult}
            />
          </div>
        </header>

        <main
          id="clairo-app"
          className={`clairo-main app-layer ${settled && activeTab === "Clairo.AI" ? "clairo-main--hero" : ""}`}
        >
          <div
            className={`intro-reveal-target ${revealing ? "intro-reveal-target--visible" : ""}`}
            style={{ transitionDelay: "60ms" }}
          >
            <div className="clairo-content">
              {activeTab === "Clairo.AI" && (
                <ClairoAISection
                  uploadResult={uploadResult}
                  onUploadResult={onUploadResult}
                  onUpdateClaim={onUpdateClaim}
                  appealViability={appealViability}
                />
              )}
              {activeTab === "Appeal Letter" && (
                <AppealLetterSection
                  uploadResult={uploadResult}
                  onGoToIntake={goToIntake}
                  onPolicyRetrieved={onPolicyRetrieved}
                  appealData={appealData}
                  appealViability={appealViability}
                  appealLetterText={appealLetterText}
                  onAppealGenerated={onAppealGenerated}
                  onAppealLetterChange={onAppealLetterChange}
                  onExportCompleted={onExportCompleted}
                  onResetAppeal={onResetAppeal}
                />
              )}
              <div
                className={activeTab === "Prior Authorization" ? "" : "hidden"}
                aria-hidden={activeTab !== "Prior Authorization"}
              >
                <PriorAuthSection
                  uploadResult={uploadResult}
                  onGoToIntake={goToIntake}
                  isActive={activeTab === "Prior Authorization"}
                />
              </div>
              {activeTab === "Analytics" && (
                <AnalyticsSection uploadResult={uploadResult} />
              )}
              {activeTab === "Claims" && <ClaimsDashboard onLoadClaim={onLoadClaim} />}
              {activeTab === "Policies" && <PolicyLibrary />}
              {activeTab === "Audit Log" && <AuditLogPanel />}
              {activeTab === "InsForge" && (
                <InsforgePanel />
              )}
            </div>
          </div>

          {activeTab !== "Clairo.AI" && (
            <footer
              className={`clairo-footer intro-reveal-target ${revealing ? "intro-reveal-target--visible" : ""}`}
              style={{ transitionDelay: "100ms" }}
            >
              <span className="clairo-footer__brand">
                <BrandMark />
              </span>
              <span className="clairo-footer__sep" aria-hidden="true">
                ·
              </span>
              <span className="status-dot" />
              <span>Backend: {API_BASE_URL.replace(/^https?:\/\//, "")}</span>
            </footer>
          )}
        </main>
      </div>
    </div>
  );

  return (
    <LayoutGroup>
      <BeamsBackground intensity="strong" className="min-h-screen">
        {dashboardShell}
      </BeamsBackground>
    </LayoutGroup>
  );
}
