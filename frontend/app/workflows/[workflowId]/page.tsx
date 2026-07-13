import { AppShell } from "@/components/layout/app-shell";
import { WorkflowDetailView } from "@/components/workflows/workflow-detail-view";

interface WorkflowDetailPageProps {
  params: Promise<{
    workflowId: string;
  }>;
}

export default async function WorkflowDetailPage({
  params,
}: WorkflowDetailPageProps) {
  const { workflowId } = await params;

  return (
    <AppShell
      title="Workflow detail"
      description="Read-only workflow state and recent persisted event backlog."
    >
      <WorkflowDetailView workflowId={workflowId} />
    </AppShell>
  );
}
