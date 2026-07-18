import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-background">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center gap-8 px-6 py-16">
        <div className="max-w-4xl">
          <p className="text-sm font-medium text-muted-foreground">
            Multi-Agent System
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-foreground md:text-6xl">
            Enterprise Multi-Agent OS
          </h1>
          <p className="mt-5 text-lg leading-8 text-muted-foreground">
            Procurement workflow automation using a LangGraph-based multi-agent
            system. This is not a chatbot; it is a controlled workflow
            orchestration platform with deterministic services, human approval,
            RAG evidence, audit events, and production-demo operations.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Link
            className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:opacity-95"
            href="/demo"
          >
            Start Demo
          </Link>
          <Link
            className="inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium hover:bg-muted"
            href="/login"
          >
            Login
          </Link>
          <a
            className="inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium hover:bg-muted"
            href="/docs/final/README.md"
          >
            Final Evaluation Docs
          </a>
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          <InfoCard
            title="Workflow first"
            description="Run a seeded procurement workflow to WAITING_APPROVAL, then approve and resume explicitly."
          />
          <InfoCard
            title="Evidence grounded"
            description="Optional RAG mode attaches retrieved citations when enabled and ingested; empty evidence is shown honestly."
          />
          <InfoCard
            title="Operationally packaged"
            description="Docker Compose, readiness checks, structured logs, metrics, CI gates, and final evaluation assets are included."
          />
        </section>
      </section>
    </main>
  );
}

function InfoCard({ title, description }: { title: string; description: string }) {
  return (
    <article className="rounded-lg border bg-card p-5 text-card-foreground shadow-sm">
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        {description}
      </p>
    </article>
  );
}
