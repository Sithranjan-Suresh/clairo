import { useState } from "react";
import UploadPanel from "./UploadPanel";
import ClaimOverviewHero from "./clairo-intake/ClaimOverviewHero";
import ClaimMetricCards from "./clairo-intake/ClaimMetricCards";
import AIAppealRecommendation from "./clairo-intake/AIAppealRecommendation";
import WorkflowProgressSection from "./clairo-intake/WorkflowProgressSection";
import ClaimWorkspace from "./clairo-intake/ClaimWorkspace";

export default function ClairoAISection({
  uploadResult,
  onUploadResult,
  onUpdateClaim,
  appealViability,
}) {
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState("overview");
  const [expandedMetricCard, setExpandedMetricCard] = useState(null);
  const [isEditingExtractedFields, setIsEditingExtractedFields] = useState(false);

  const hasUpload = Boolean(uploadResult);
  const hasExtractedClaim = Boolean(uploadResult?.structured_claim);

  return (
    <div className="clairo-ai-page">
      <div className="clairo-ai-page__content">
        <div className="claim-intake claim-intake--v2">
          <header className="claim-intake__header">
            <h1
              className="claim-intake__title"
              style={{ fontFamily: '"DM Serif Display", serif', fontStyle: "italic" }}
            >
              Claim Intake
            </h1>
            <p className="claim-intake__subtitle font-body">
              Upload a denial, review extracted fields, and prepare your appeal workflow.
            </p>
          </header>

          {!hasUpload ? (
            <div className="claim-intake__upload-primary">
              <UploadPanel onResult={onUploadResult} />
            </div>
          ) : (
            <>
              <WorkflowProgressSection uploadResult={uploadResult} />

              {hasExtractedClaim && (
                <ClaimOverviewHero uploadResult={uploadResult} />
              )}

              {hasExtractedClaim && (
                <ClaimMetricCards
                  uploadResult={uploadResult}
                  expandedMetricCard={expandedMetricCard}
                  onToggle={setExpandedMetricCard}
                />
              )}

              {hasExtractedClaim && (
                <AIAppealRecommendation
                  uploadResult={uploadResult}
                  appealViability={appealViability}
                />
              )}

              {hasExtractedClaim && (
                <ClaimWorkspace
                  uploadResult={uploadResult}
                  onUpdateClaim={onUpdateClaim}
                  activeWorkspaceTab={activeWorkspaceTab}
                  setActiveWorkspaceTab={setActiveWorkspaceTab}
                  isEditingExtractedFields={isEditingExtractedFields}
                  setIsEditingExtractedFields={setIsEditingExtractedFields}
                />
              )}

              <details className="claim-intake__reupload">
                <summary className="claim-intake__reupload-summary">Upload a different denial</summary>
                <UploadPanel onResult={onUploadResult} />
              </details>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
