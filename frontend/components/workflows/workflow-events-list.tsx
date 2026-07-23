import type { WorkflowEvent } from "@/lib/api/types";

interface WorkflowEventsListProps {
  events: WorkflowEvent[];
}

export function WorkflowEventsList({ events }: WorkflowEventsListProps) {
  if (events.length === 0) {
    return (
      <div className="ops-panel p-5">
        <h2 className="text-sm font-semibold">Recent events</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          No persisted workflow events are available yet.
        </p>
      </div>
    );
  }

  return (
    <div className="ops-panel p-5">
      <h2 className="text-sm font-semibold">Recent events</h2>
      <ol className="mt-4 grid gap-3">
        {events.map((event) => (
          <li className="rounded-md border border-border/70 bg-background/55 p-3" key={event.event_id}>
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm font-medium">{event.event_type}</p>
              <p className="text-xs text-muted-foreground">
                {formatDate(event.created_at)}
              </p>
            </div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {event.message ?? event.status ?? "Persisted workflow event"}
            </p>
            {event.agent_name ? (
              <p className="mt-2 text-xs text-muted-foreground">
                Stage: {event.agent_name}
              </p>
            ) : null}
          </li>
        ))}
      </ol>
    </div>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
