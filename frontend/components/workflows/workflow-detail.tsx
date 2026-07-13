import { WorkflowEventsList } from "@/components/workflows/workflow-events-list";
import { WorkflowStatusBadge } from "@/components/workflows/workflow-status-badge";
import type { WorkflowEvent, WorkflowState } from "@/lib/api/types";

interface WorkflowDetailProps {
  workflow: WorkflowState;
  events: WorkflowEvent[];
}

export function WorkflowDetail({ workflow, events }: WorkflowDetailProps) {
  return (
    <div className="grid gap-6">
      <section className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              Workflow detail
            </p>
            <h2 className="mt-2 break-all text-2xl font-semibold tracking-tight">
              {workflow.workflow_id}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {workflow.workflow_type}
              {workflow.domain ? ` / ${workflow.domain}` : ""}
            </p>
          </div>
          <WorkflowStatusBadge status={workflow.status} />
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <InfoCard title="Current step" value={workflow.current_step ?? "Not started"} />
        <InfoCard title="Retry count" value={String(workflow.retry_count ?? 0)} />
        <InfoCard
          title="Updated"
          value={formatDate(workflow.updated_at ?? workflow.created_at)}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <JsonCard title="Request summary" value={workflow.request} />
        <JsonCard title="Metadata" value={workflow.metadata ?? {}} />
        <JsonCard title="Customer" value={workflow.customer ?? {}} />
        <JsonCard title="Items" value={workflow.items ?? []} />
      </section>

      {workflow.error ? (
        <section className="rounded-lg border border-destructive/30 bg-card p-5 text-card-foreground shadow-sm">
          <h2 className="text-sm font-semibold text-destructive">
            Workflow error
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {workflow.error.message}
          </p>
        </section>
      ) : null}

      <WorkflowEventsList events={events} />
    </div>
  );
}

function InfoCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-5 text-card-foreground shadow-sm">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{value}</p>
    </div>
  );
}

function JsonCard({ title, value }: { title: string; value: unknown }) {
  return (
    <div className="rounded-lg border bg-card p-5 text-card-foreground shadow-sm">
      <h3 className="text-sm font-semibold">{title}</h3>
      <pre className="mt-3 max-h-72 overflow-auto rounded-md bg-muted p-3 text-xs leading-5 text-muted-foreground">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
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
