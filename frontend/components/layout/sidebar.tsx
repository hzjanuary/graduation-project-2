import { NavLink } from "@/components/navigation/nav-link";

const navigationItems = [
  { href: "/demo", label: "Demo Command" },
  { href: "/agent-monitor", label: "Agent Monitor" },
  { href: "/workflows", label: "Workflows" },
  { href: "/workflows/new", label: "Create Workflow" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/events", label: "Runtime Events" },
] as const;

export function Sidebar() {
  return (
    <aside className="border-b border-border/70 bg-card/80 px-4 py-4 text-card-foreground backdrop-blur md:sticky md:top-0 md:min-h-screen md:w-72 md:border-b-0 md:border-r">
      <div className="flex flex-col gap-6">
        <div className="rounded-lg border border-primary/20 bg-background/50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
            Multi-Agent OS
          </p>
          <p className="mt-2 text-sm font-semibold text-foreground">
            Violet Operations Console
          </p>
          <p className="mt-3 inline-flex rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-xs font-medium text-emerald-200">
            Deterministic no-key demo
          </p>
        </div>
        <nav
          className="grid gap-1 sm:grid-cols-2 md:flex md:flex-col"
          aria-label="Dashboard navigation"
        >
          {navigationItems.map((item) => (
            <NavLink key={item.href} href={item.href} label={item.label} />
          ))}
        </nav>
      </div>
    </aside>
  );
}
