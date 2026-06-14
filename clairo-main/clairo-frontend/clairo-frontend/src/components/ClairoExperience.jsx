import { useEffect, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import { motion, LayoutGroup } from "framer-motion";
import { ShaderAnimation } from "@/components/ui/shader-animation";
import { BeamsBackground } from "@/components/ui/beams-background";
import TopDockNav from "./TopDockNav";
import ClairoAISection from "./ClairoAISection";
import AppealLetterSection from "./AppealLetterSection";
import AnalyticsSection from "./AnalyticsSection";
import PriorAuthSection from "./PriorAuthSection";
import InsforgePanel from "./InsforgePanel";
import { BrandMark } from "./BrandMark";
import ClairoLogo from "./ClairoLogo";
import { API_BASE_URL } from "../api";

const INTRO_PHASE = {
  SHADER: "shader",
  FADE: "fade",
  COLLAPSE: "collapse",
  REVEAL: "reveal",
  SETTLED: "settled",
};

const LETTERS = [
  { char: "C", mergeX: 92 },
  { char: "L", mergeX: 46 },
  { char: "Δ", mergeX: 0, isLogo: true },
  { char: "I", mergeX: -46 },
  { char: "R", mergeX: -92 },
  { char: "O", mergeX: -138 },
];

const COLLAPSE_MS = 800;
const REVEAL_MS = 600;
const SHADER_MS = 2500;
const FADE_MS = 1300;

const collapseEase = [0.42, 0, 0.58, 1];
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
}) {
  const goToIntake = () => setActiveTab("Clairo.AI");
  const [phase, setPhase] = useState(() => {
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      return INTRO_PHASE.SETTLED;
    }
    return INTRO_PHASE.SHADER;
  });

  const settled = phase === INTRO_PHASE.SETTLED;
  const showOverlay = phase !== INTRO_PHASE.SETTLED;
  const showWordmark = phase === INTRO_PHASE.COLLAPSE;
  const showHeaderDelta =
    phase === INTRO_PHASE.REVEAL || phase === INTRO_PHASE.SETTLED;
  const collapsing = phase === INTRO_PHASE.COLLAPSE;
  const revealing = phase === INTRO_PHASE.REVEAL || settled;
  const shaderFading =
    phase === INTRO_PHASE.FADE ||
    phase === INTRO_PHASE.COLLAPSE ||
    phase === INTRO_PHASE.REVEAL;
  const handleShaderComplete = useCallback(() => {
    setPhase(INTRO_PHASE.FADE);
  }, []);

  useEffect(() => {
    if (phase === INTRO_PHASE.FADE) {
      const id = window.setTimeout(
        () => setPhase(INTRO_PHASE.COLLAPSE),
        FADE_MS,
      );
      return () => window.clearTimeout(id);
    }
    if (phase === INTRO_PHASE.COLLAPSE) {
      const id = window.setTimeout(
        () => setPhase(INTRO_PHASE.REVEAL),
        COLLAPSE_MS,
      );
      return () => window.clearTimeout(id);
    }
    if (phase === INTRO_PHASE.REVEAL) {
      const id = window.setTimeout(
        () => setPhase(INTRO_PHASE.SETTLED),
        REVEAL_MS,
      );
      return () => window.clearTimeout(id);
    }
  }, [phase]);

  useEffect(() => {
    if (phase !== INTRO_PHASE.SETTLED) return;
    document.querySelectorAll(".shader-wordmark__char").forEach((el) => {
      if (el instanceof HTMLElement) el.style.willChange = "auto";
    });
  }, [phase]);

  useEffect(() => {
    if (settled) {
      document.documentElement.style.overflow = "";
      document.body.style.overflow = "";
      return;
    }

    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";

    return () => {
      document.documentElement.style.overflow = "";
      document.body.style.overflow = "";
    };
  }, [settled]);

  const introOverlay =
    showOverlay &&
    createPortal(
      <div
        className={`intro-overlay ${revealing ? "intro-overlay--exit" : ""}`}
        aria-hidden={revealing}
      >
        <div
          className={`intro-overlay__shader ${shaderFading ? "intro-overlay__shader--fade" : ""}`}
        >
          <ShaderAnimation
            durationMs={SHADER_MS}
            onComplete={handleShaderComplete}
          />
        </div>
        {showWordmark && (
          <motion.div
            className="intro-wordmark"
            aria-label="CLΔIRO"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.7, ease: [0.4, 0, 0.2, 1] }}
          >
            <h1 className="shader-wordmark">
              {LETTERS.map(({ char, mergeX, isLogo }, index) => (
                <motion.span
                  key={char}
                  layoutId={isLogo ? "clairo-delta" : undefined}
                  className={
                    isLogo
                      ? "shader-wordmark__char shader-wordmark__char--logo brand-mark__logo-wrap"
                      : "shader-wordmark__char brand-mark__text"
                  }
                  initial={false}
                  animate={
                    collapsing
                      ? isLogo
                        ? { opacity: 1, scale: 1, x: 0 }
                        : {
                            opacity: 0,
                            scale: 0,
                            x: mergeX,
                          }
                      : { opacity: 1, scale: 1, x: 0 }
                  }
                  transition={{
                    duration: COLLAPSE_MS / 1000,
                    ease: collapseEase,
                    delay: isLogo ? 0 : index * 0.04,
                  }}
                  style={{
                    willChange: collapsing ? "transform, opacity" : "auto",
                  }}
                >
                  {isLogo ? (
                    <ClairoLogo inline className="shader-wordmark__logo" />
                  ) : (
                    char
                  )}
                </motion.span>
              ))}
            </h1>
          </motion.div>
        )}
      </div>,
      document.body,
    );

  const dashboardShell = (
    <div
      className={`app ${settled ? "app--settled" : "app--intro"} ${revealing || settled ? "app--with-beams" : ""} ${settled && activeTab === "Clairo.AI" ? "app--clairo-page" : ""}`}
    >
      <div
        className={`app-shell app-shell--content ${revealing ? "app-shell--revealed" : "app-shell--prepared"}`}
      >
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
      {introOverlay}
      {revealing || settled ? (
        <BeamsBackground intensity="strong" className="min-h-screen">
          {dashboardShell}
        </BeamsBackground>
      ) : (
        dashboardShell
      )}
    </LayoutGroup>
  );
}
