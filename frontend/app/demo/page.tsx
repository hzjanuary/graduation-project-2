import Link from "next/link";

import { DemoWorkflowCards } from "@/components/demo/demo-workflow-cards";
import { demoWorkflows, localDemoAccounts, workflowLifecycle } from "@/lib/demo";

export default function DemoPage() {
  return (
    <main className="min-h-screen bg-background">
      <section className="mx-auto grid w-full max-w-7xl gap-8 px-6 py-10">
        <div className="flex flex-col gap-4">
          <p className="text-sm font-medium text-muted-foreground">
            Evaluator start here
          </p>
          <div className="max-w-4xl">
            <h1 className="text-4xl font-semibold tracking-tight text-foreground">
              Enterprise Multi-Agent OS demo command center
            </h1>
            <p className="mt-4 text-base leading-7 text-muted-foreground">
              This is not a chatbot. It is a procurement workflow orchestration
              system with deterministic workflow state, specialized runtime
              stages, human approval, evidence/citations, persisted events, and
              production-demo operations.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
              href="/login"
            >
              Go to Login
            </Link>
            <Link
              className="inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium hover:bg-muted"
              href="/workflows"
            >
              Open Workflows
            </Link>
            <Link
              className="inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium hover:bg-muted"
              href={`/workflows/${demoWorkflows[0].workflowId}`}
            >
              Full demo: Created workflow
            </Link>
          </div>
        </div>

        <section className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
          <h2 className="text-lg font-semibold">Operation map</h2>
          <div className="mt-5 grid gap-3 md:grid-cols-6">
            {workflowLifecycle.map((step, index) => (
              <div
                className="rounded-md border bg-background p-4 text-center"
                key={step}
              >
                <p className="text-xs font-medium text-muted-foreground">
                  Step {index + 1}
                </p>
                <p className="mt-2 text-sm font-semibold">{step}</p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            The runtime intentionally stops at WAITING_APPROVAL. Review the
            workflow details, evidence, and event timeline before submitting a
            human approval decision. Resume is a separate action after approval.
          </p>
        </section>

        <section className="grid gap-4 lg:grid-cols-4">
          {localDemoAccounts.map((account) => (
            <article
              className="rounded-lg border bg-card p-5 text-card-foreground shadow-sm"
              key={account.email}
            >
              <p className="text-sm font-medium text-muted-foreground">
                {account.role}
              </p>
              <h3 className="mt-2 break-all text-base font-semibold">
                {account.email}
              </h3>
              <p className="mt-2 break-all rounded-md bg-muted px-3 py-2 text-sm">
                {account.password}
              </p>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                {account.recommendation}
              </p>
            </article>
          ))}
        </section>

        <section className="grid gap-4">
          <div>
            <h2 className="text-lg font-semibold">Choose a seeded workflow</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              These IDs come from the explicit local demo seed. They are links
              to backend workflow records, not fabricated frontend data.
            </p>
          </div>
          <DemoWorkflowCards />
        </section>

        <section className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
          <h2 className="text-lg font-semibold">Optional RAG evidence mode</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            RAG is off by default. Evidence and citations appear only when
            RAG_ENABLED=true and demo knowledge ingestion has been run. The
            frontend shows attached evidence from workflow state/events and does
            not fabricate evidence when none exists.
          </p>
        </section>
      </section>
    </main>
  );
}
