import type { WorkflowState } from "@/lib/api/types";

interface WorkflowNextStepGuideProps {
  status: WorkflowState["status"];
}

export function WorkflowNextStepGuide({ status }: WorkflowNextStepGuideProps) {
  const guide = nextStepGuide(status);

  return (
    <section className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">
            What should I do next?
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">
            {guide.title}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            {guide.description}
          </p>
        </div>
        <span className="inline-flex w-fit rounded-full border px-3 py-1.5 text-xs font-medium text-muted-foreground">
          {status}
        </span>
      </div>
      <div className="mt-5 rounded-md border bg-muted/40 p-4">
        <p className="text-sm font-semibold">Primary next action</p>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {guide.action}
        </p>
      </div>
    </section>
  );
}

function nextStepGuide(status: WorkflowState["status"]) {
  switch (status) {
    case "CREATED":
      return {
        title: "This workflow has not run yet.",
        description:
          "Start the runtime from the Run panel. The expected demo result is WAITING_APPROVAL, not automatic completion.",
        action: "Click Run workflow, then review the approval boundary.",
      };
    case "WAITING_APPROVAL":
      return {
        title: "Runtime has stopped at the human approval boundary.",
        description:
          "Review the workflow details, evidence if available, approval package, and event timeline before making a decision.",
        action: "Submit approval when the workflow is ready to continue.",
      };
    case "APPROVED":
      return {
        title: "Approval is complete; continuation is ready.",
        description:
          "The workflow is approved and waiting for the explicit resume action. Resume uses /resume, not /run.",
        action: "Click Resume workflow to run post-approval continuation.",
      };
    case "COMPLETED":
      return {
        title: "Workflow is complete.",
        description:
          "Use this state to review final workflow output, approval history, evidence, and the event timeline.",
        action: "Review timeline, approval history, evidence, and final state.",
      };
    case "REJECTED":
      return {
        title: "Workflow was rejected.",
        description:
          "Rejected workflows are terminal. They are useful for demonstrating governance and audit history.",
        action: "Review the approval history and timeline; no resume action is available.",
      };
    case "FAILED":
    case "CANCELLED":
      return {
        title: "Workflow is in a terminal non-happy-path state.",
        description:
          "The backend remains authoritative for terminal workflow behavior and error details.",
        action: "Review workflow error details and timeline events.",
      };
    default:
      return {
        title: "Workflow is running through deterministic runtime stages.",
        description:
          "Refresh detail and timeline evidence as the backend advances the workflow.",
        action: "Wait for the next stable workflow state before approving or resuming.",
      };
  }
}
