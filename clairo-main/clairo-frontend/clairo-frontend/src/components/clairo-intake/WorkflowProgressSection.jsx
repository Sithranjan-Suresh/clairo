import WorkflowStepper from "../saas/WorkflowStepper";

export default function WorkflowProgressSection({ uploadResult }) {
  return (
    <section className="workflow-progress" aria-label="Workflow progress">
      <WorkflowStepper uploadResult={uploadResult} />
    </section>
  );
}
