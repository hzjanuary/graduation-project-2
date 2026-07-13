import { AppShell } from "@/components/layout/app-shell";
import { WorkflowCreateForm } from "@/components/workflows/workflow-create-form";

export default function CreateWorkflowPage() {
  return (
    <AppShell
      title="Create Workflow"
      description="Create a procurement quotation workflow through the existing backend API."
    >
      <WorkflowCreateForm />
    </AppShell>
  );
}
