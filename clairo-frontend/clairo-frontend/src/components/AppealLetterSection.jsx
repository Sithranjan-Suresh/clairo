import AppealPanel from "./AppealPanel";
import EmptyState from "./saas/EmptyState";

export default function AppealLetterSection({
  uploadResult,
  onGoToIntake,
  onPolicyRetrieved,
  appealData,
  appealViability,
  appealLetterText,
  onAppealGenerated,
  onAppealLetterChange,
  onExportCompleted,
  onResetAppeal,
}) {
  if (!uploadResult?.structured_claim) {
    return (
      <div className="section-stack section-fade appeal-page">
        <EmptyState
          icon="✍️"
          title="No claim selected"
          description="Upload a denial first to generate an appeal letter and retrieve coverage evidence."
          onAction={onGoToIntake}
        />
      </div>
    );
  }

  return (
    <div className="section-stack section-fade appeal-page">
      <header className="appeal-page__header">
        <h1
          className="appeal-page__title"
          style={{ fontFamily: '"DM Serif Display", serif', fontStyle: "italic" }}
        >
          Appeal Letter
        </h1>
        <p className="appeal-page__subtitle font-body">
          Generate a payer-ready appeal and review the supporting coverage evidence in one place.
        </p>
      </header>

      <AppealPanel
        uploadResult={uploadResult}
        onPolicyRetrieved={onPolicyRetrieved}
        appealData={appealData}
        appealViability={appealViability}
        appealLetterText={appealLetterText}
        onAppealGenerated={onAppealGenerated}
        onAppealLetterChange={onAppealLetterChange}
        onExportCompleted={onExportCompleted}
        onResetAppeal={onResetAppeal}
      />
    </div>
  );
}
