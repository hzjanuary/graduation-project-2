import { AgentMonitorView } from "@/components/agent-monitor/agent-monitor-view";
import { AppShell } from "@/components/layout/app-shell";

interface AgentMonitorPageProps {
  searchParams?: Promise<{
    workflowId?: string | string[];
  }>;
}

export default async function AgentMonitorPage({
  searchParams,
}: AgentMonitorPageProps) {
  const params = searchParams ? await searchParams : {};
  const rawWorkflowId = params.workflowId;
  const workflowId = Array.isArray(rawWorkflowId)
    ? rawWorkflowId[0]
    : rawWorkflowId;

  return (
    <AppShell
      title="Agent Monitor"
      description="Live demo observer mode for workflow stages, events, and approval boundaries."
    >
      <AgentMonitorView workflowId={workflowId} />
    </AppShell>
  );
}
