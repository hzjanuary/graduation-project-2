import Link from "next/link";

import { DemoWorkflowCards } from "@/components/demo/demo-workflow-cards";
import { AppShell } from "@/components/layout/app-shell";

export default function DashboardPage() {
  return (
    <AppShell
      title="Workflow dashboard"
      description="Operator overview for running the procurement workflow demo."
    >
      <div className="grid gap-6">
        <section className="grid gap-4 lg:grid-cols-2">
          <DashboardCard
            title="Start here"
            description="Open the demo command center for local-demo accounts, seeded workflow choices, and the run/approve/resume sequence."
            href="/demo"
            linkLabel="Open Demo Guide"
          />
          <DashboardCard
            title="Workflow lifecycle"
            description="Run starts deterministic orchestration and stops at WAITING_APPROVAL. Human approval is required before the explicit resume action completes the workflow."
            href="/workflows"
            linkLabel="Open Workflows"
          />
        </section>

        <section className="grid gap-4">
          <div>
            <h2 className="text-lg font-semibold">Primary demo workflows</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Use the CREATED workflow for the full demo, or choose a later
              status when time is short.
            </p>
          </div>
          <DemoWorkflowCards compact />
        </section>

        <section className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
          <h2 className="text-lg font-semibold">Quality and evidence</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Final proof comes from the documented quality gates and E2E demo
            script. Use scripts/final/final-quality-gate.sh for the final
            non-mutating gate and scripts/final/e2e-demo-validation.sh with
            --confirm-local-demo for the full lifecycle validation.
          </p>
        </section>
      </div>
    </AppShell>
  );
}

function DashboardCard({
  title,
  description,
  href,
  linkLabel,
}: {
  title: string;
  description: string;
  href: string;
  linkLabel: string;
}) {
  return (
    <article className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        {description}
      </p>
      <Link
        className="mt-5 inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
        href={href}
      >
        {linkLabel}
      </Link>
    </article>
  );
}
