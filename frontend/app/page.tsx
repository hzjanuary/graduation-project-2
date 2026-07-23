import Link from "next/link";

export default function HomePage() {
  return (
    <main className="ops-page">
      <section className="mx-auto grid min-h-screen w-full max-w-7xl gap-10 px-5 py-10 sm:px-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(340px,0.9fr)] lg:items-center lg:px-8">
        <div className="max-w-4xl">
          <p className="ops-kicker">Multi-Agent System</p>
          <h1 className="mt-5 text-5xl font-semibold tracking-tight text-foreground md:text-7xl">
            Enterprise workflow OS.
          </h1>
          <p className="mt-6 max-w-3xl text-base leading-7 text-muted-foreground md:text-lg md:leading-8">
            Enterprise Multi-Agent OS is not a chatbot. It is a controlled
            procurement workflow platform where deterministic services,
            specialized stages, human approval, RAG evidence, audit events, and
            operational readiness work as one system.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link className="ops-button-primary" href="/demo">
              Start Demo
            </Link>
            <Link className="ops-button-secondary" href="/login">
              Login
            </Link>
            <a className="ops-button-secondary" href="/docs/final/README.md">
              Final Evaluation Docs
            </a>
          </div>
        </div>

        <section className="ops-panel-strong grid gap-4 p-5">
          <div className="rounded-lg border border-primary/25 bg-primary/10 p-4">
            <p className="ops-kicker">Defense path</p>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Telegram RFQ - extraction - normalization - workflow run -
              WAITING_APPROVAL - Manager approval - resume - COMPLETED.
            </p>
          </div>
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
    <article className="ops-panel-muted p-5">
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        {description}
      </p>
    </article>
  );
}
