import { useState } from "react";
import { WovenLightHero } from "@/components/ui/woven-light-hero";
import ClairoExperience from "./components/ClairoExperience";
import { normalizeAppealConfidence } from "./utils/appealConfidence";
import "./index.css";

function formatLetterText(text) {
  return (text ?? "").replace(/\\n/g, "\n");
}

export default function App() {
  const [showShader, setShowShader] = useState(false);
  const [activeTab, setActiveTab] = useState("Clairo.AI");
  const [uploadResult, setUploadResult] = useState(null);
  const [appealData, setAppealData] = useState(null);
  const [appealViability, setAppealViability] = useState(null);
  const [appealLetterText, setAppealLetterText] = useState(null);

  function resetAppealSession() {
    setAppealData(null);
    setAppealViability(null);
    setAppealLetterText(null);
  }

  function handleUploadResult(data) {
    resetAppealSession();
    setUploadResult({
      ...data,
      policy_retrieved: false,
      policy_matches_count: 0,
      appeal_generated: false,
      export_completed: false,
      appeal_confidence: null,
    });
  }

  function handleUpdateClaim(structured_claim) {
    setUploadResult((prev) =>
      prev ? { ...prev, structured_claim: { ...prev.structured_claim, ...structured_claim } } : prev,
    );
  }

  function handlePolicyRetrieved(count, source) {
    setUploadResult((prev) =>
      prev
        ? {
            ...prev,
            policy_matches_count: count,
            policy_retrieved: true,
            policy_source: source ?? prev.policy_source,
          }
        : prev,
    );
  }

  function handleAppealGenerated(result, viability) {
    const letter = formatLetterText(result?.appeal_letter);
    setAppealData(result);
    setAppealViability(viability ?? null);
    setAppealLetterText(letter);
    setUploadResult((prev) =>
      prev
        ? {
            ...prev,
            appeal_generated: true,
            export_completed: false,
            appeal_confidence:
              result?.confidence_score != null
                ? normalizeAppealConfidence(result.confidence_score)
                : prev.appeal_confidence,
          }
        : prev,
    );
  }

  function handleAppealLetterChange(text) {
    const formatted = formatLetterText(text);
    setAppealLetterText(formatted);
    setAppealData((prev) => (prev ? { ...prev, appeal_letter: formatted } : prev));
  }

  function handleExportCompleted() {
    setUploadResult((prev) =>
      prev ? { ...prev, export_completed: true } : prev,
    );
  }

  function handleResetAppeal() {
    resetAppealSession();
    setUploadResult((prev) =>
      prev
        ? {
            ...prev,
            appeal_generated: false,
            export_completed: false,
            appeal_confidence: null,
          }
        : prev,
    );
  }

  return (
    <>
      {!showShader ? (
        <WovenLightHero onExplore={() => setShowShader(true)} />
      ) : (
        <ClairoExperience
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          uploadResult={uploadResult}
          onUploadResult={handleUploadResult}
          onUpdateClaim={handleUpdateClaim}
          onPolicyRetrieved={handlePolicyRetrieved}
          appealData={appealData}
          appealViability={appealViability}
          appealLetterText={appealLetterText}
          onAppealGenerated={handleAppealGenerated}
          onAppealLetterChange={handleAppealLetterChange}
          onExportCompleted={handleExportCompleted}
          onResetAppeal={handleResetAppeal}
        />
      )}
    </>
  );
}
