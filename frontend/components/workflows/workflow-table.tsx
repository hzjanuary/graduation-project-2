import Link from "next/link";

import { WorkflowStatusBadge } from "@/components/workflows/workflow-status-badge";
import type { WorkflowState } from "@/lib/api/types";

interface WorkflowTableProps {
  workflows: WorkflowState[];
}

export function WorkflowTable({ workflows }: WorkflowTableProps) {
  if (workflows.length === 0) {
    return (
      <div className="ops-panel p-6">
        <h2 className="text-base font-semibold">No workflows yet</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Workflow records from the backend will appear here after they are
          created from the Create Workflow page.
        </p>
      </div>
    );
  }

  return (
    <div className="ops-table">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-border/70 bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">Workflow</th>
              <th className="px-4 py-3 font-medium">Type / Domain</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Current step</th>
              <th className="px-4 py-3 font-medium">Updated</th>
              <th className="px-4 py-3 font-medium">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {workflows.map((workflow) => (
              <tr className="ops-table-row" key={workflow.workflow_id}>
                <td className="px-4 py-4 font-medium">
                  {shortWorkflowId(workflow.workflow_id)}
                </td>
                <td className="px-4 py-4 text-muted-foreground">
                  <div>{workflow.workflow_type}</div>
                  <div className="text-xs">{workflow.domain ?? "No domain"}</div>
                </td>
                <td className="px-4 py-4">
                  <WorkflowStatusBadge status={workflow.status} />
                </td>
                <td className="px-4 py-4 text-muted-foreground">
                  {workflow.current_step ?? "Not started"}
                </td>
                <td className="px-4 py-4 text-muted-foreground">
                  {formatDate(workflow.updated_at ?? workflow.created_at)}
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-3">
                    <Link
                      className="text-sm font-semibold text-primary hover:underline"
                      href={`/workflows/${workflow.workflow_id}`}
                    >
                      View detail
                    </Link>
                    <Link
                      className="text-sm font-semibold text-sky-300 hover:underline"
                      href={`/agent-monitor?workflowId=${workflow.workflow_id}`}
                    >
                      Monitor
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function shortWorkflowId(workflowId: string): string {
  return workflowId.length > 12 ? `${workflowId.slice(0, 8)}...` : workflowId;
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Not recorded";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
