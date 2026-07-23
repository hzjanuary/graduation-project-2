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
          className="ops-card-link group p-5"
          href={`/workflows/${workflow.workflowId}`}
          key={workflow.workflowId}
        >
          <p className="ops-kicker">
            {workflow.title}
          </p>
          <h3 className="mt-2 text-base font-semibold">
            {workflow.shortTitle}
          </h3>
          <p className="mt-2 inline-flex rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
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
