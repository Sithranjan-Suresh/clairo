import PolicyPanel from "./PolicyPanel";
import EmptyState from "./saas/EmptyState";

export default function PolicyCitationsSection({
  uploadResult,
  onGoToIntake,
  onPolicyRetrieved,
}) {
  if (!uploadResult?.structured_claim) {
    return (
      <div className="section-stack section-fade">
        <EmptyState
          icon="📚"
          title="No coverage evidence yet"
          description="Upload a denial to retrieve payer policy citations that support your appeal."
          onAction={onGoToIntake}
        />
      </div>
    );
  }

  return (
    <div className="section-stack section-fade">
      <PolicyPanel
        uploadResult={uploadResult}
        onPolicyRetrieved={onPolicyRetrieved}
      />
    </div>
  );
}
