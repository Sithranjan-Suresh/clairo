import PriorAuthPanel from "./PriorAuthPanel";

export default function PriorAuthSection({ uploadResult, onGoToIntake, isActive = true }) {
  return (
    <div className="section-stack section-fade">
      <PriorAuthPanel
        uploadResult={uploadResult}
        onGoToIntake={onGoToIntake}
        isActive={isActive}
      />
    </div>
  );
}
