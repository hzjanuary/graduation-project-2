import { AppShell } from "@/components/layout/app-shell";
import { WorkflowListView } from "@/components/workflows/workflow-list-view";

export default function WorkflowsPage() {
  return (
    <AppShell
      title="Workflows"
      description="Read-only workflow list backed by the existing workflow API."
    >
      <WorkflowListView />
    </AppShell>
  );
}
