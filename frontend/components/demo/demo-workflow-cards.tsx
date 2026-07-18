import Link from "next/link";

import { demoWorkflows } from "@/lib/demo";

interface DemoWorkflowCardsProps {
  compact?: boolean;
}

export function DemoWorkflowCards({ compact = false }: DemoWorkflowCardsProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-4">
      {demoWorkflows.map((workflow) => (
        <Link
          className="rounded-lg border bg-card p-5 text-card-foreground shadow-sm transition hover:border-primary/60 hover:bg-muted/30"
          href={`/workflows/${workflow.workflowId}`}
          key={workflow.workflowId}
        >
          <p className="text-sm font-medium text-muted-foreground">
            {workflow.title}
          </p>
          <h3 className="mt-2 text-base font-semibold">
            {workflow.shortTitle}
          </h3>
          <p className="mt-2 text-xs font-medium text-primary">
            {workflow.status}
          </p>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            {workflow.purpose}
          </p>
          {compact ? null : (
            <p className="mt-3 text-xs leading-5 text-muted-foreground">
              {workflow.workflowId}
            </p>
          )}
        </Link>
      ))}
    </div>
  );
}
