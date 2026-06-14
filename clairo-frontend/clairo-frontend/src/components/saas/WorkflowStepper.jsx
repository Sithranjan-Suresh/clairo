const STEPS = [
  "Upload",
  "Extract",
  "Classify",
  "Retrieve Policy",
  "Generate Appeal",
  "Export",
];

export const WORKFLOW_STEP_COUNT = STEPS.length;

function stepStatus(index, activeIndex) {
  if (activeIndex >= STEPS.length) return "completed";
  if (index < activeIndex) return "completed";
  if (index === activeIndex) return "active";
  return "inactive";
}

export function deriveWorkflowIndex(uploadResult) {
  if (!uploadResult) return 0;
  if (!uploadResult.structured_claim) return 1;
  if (!uploadResult.classification) return 2;

  const policyDone =
    uploadResult.policy_retrieved ||
    (uploadResult.policy_matches_count != null && uploadResult.policy_matches_count > 0);
  if (!policyDone) return 3;

  if (!uploadResult.appeal_generated) return 4;
  if (!uploadResult.export_completed) return 5;

  return STEPS.length;
}

export function deriveWorkflowProgress(uploadResult) {
  const current = deriveWorkflowIndex(uploadResult);
  const completedCount = current >= STEPS.length ? STEPS.length : current;
  return Math.round((completedCount / STEPS.length) * 100);
}

export default function WorkflowStepper({ uploadResult, activeIndex }) {
  const current =
    activeIndex != null ? activeIndex : deriveWorkflowIndex(uploadResult);
  const progress = deriveWorkflowProgress(uploadResult);
  const allComplete = current >= STEPS.length;

  return (
    <nav className="workflow-stepper" aria-label="Claim workflow progress">
      <div className="workflow-stepper__header">
        <span className="workflow-stepper__progress-label">Workflow progress</span>
        <span className="workflow-stepper__progress-value" aria-live="polite">
          {progress}%
        </span>
      </div>
      <div
        className="workflow-stepper__bar"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Workflow ${progress}% complete`}
      >
        <span
          className="workflow-stepper__bar-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
      <ol className="workflow-stepper__list">
        {STEPS.map((label, index) => {
          const status = stepStatus(index, current);
          const isLast = index === STEPS.length - 1;
          const connectorDone =
            status === "completed" ||
            (status === "active" && index < current) ||
            allComplete;
          return (
            <li
              key={label}
              className={`workflow-stepper__item workflow-stepper__item--${status}`}
            >
              <div className="workflow-stepper__capsule">
                <span className="workflow-stepper__index" aria-hidden="true">
                  {status === "completed" ? "✓" : index + 1}
                </span>
                <span className="workflow-stepper__label">{label}</span>
              </div>
              {!isLast && (
                <span
                  className={`workflow-stepper__connector workflow-stepper__connector--${connectorDone ? "done" : ""}`}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
