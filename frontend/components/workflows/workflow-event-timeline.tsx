"use client";

import { useMemo, useState } from "react";

import { useWorkflowEventStream } from "@/hooks/use-workflow-event-stream";
import {
  mergeWorkflowTimelineEvents,
  safePayloadPreview,
} from "@/lib/streaming/workflow-events";
import { getAccessToken } from "@/lib/auth/session";
import type { WorkflowEvent, WorkflowTimelineEvent } from "@/lib/api/types";

interface WorkflowEventTimelineProps {
  workflowId: string;
  persistedEvents: WorkflowEvent[];
}

export function WorkflowEventTimeline({
  workflowId,
  persistedEvents,
}: WorkflowEventTimelineProps) {
  const [accessToken] = useState(() => getAccessToken());
  const { status, messages, errorMessage, reconnect } = useWorkflowEventStream({
    workflowId,
    accessToken,
  });
  const timelineEvents = useMemo(
    () => mergeWorkflowTimelineEvents(persistedEvents, messages),
    [messages, persistedEvents],
  );

  return (
    <section className="ops-panel p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="ops-kicker">
            Live monitoring
          </p>
          <h2 className="mt-1 text-lg font-semibold">Event timeline</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Combines persisted event backlog with live messages from the
            workflow WebSocket stream.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ConnectionBadge status={status} />
          <button
            className="ops-button-secondary min-h-9 px-3"
            onClick={reconnect}
            type="button"
          >
            Reconnect
          </button>
        </div>
      </div>

      {errorMessage ? (
        <div className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {errorMessage}
        </div>
      ) : null}

      {timelineEvents.length === 0 ? (
        <p className="mt-4 text-sm leading-6 text-muted-foreground">
          No workflow events are available yet.
        </p>
      ) : (
        <ol className="mt-5 grid gap-3">
          {timelineEvents.map((event) => (
            <TimelineItem event={event} key={event.event_id} />
          ))}
        </ol>
      )}
    </section>
  );
}

function ConnectionBadge({
  status,
}: {
  status: "connecting" | "connected" | "disconnected" | "error";
}) {
  const label = {
    connecting: "Stream connecting",
    connected: "Stream connected",
    disconnected: "Stream disconnected",
    error: "Stream error",
  }[status];

  return (
    <span className="ops-chip min-h-9">
      {label}
    </span>
  );
}

function TimelineItem({ event }: { event: WorkflowTimelineEvent }) {
  const payloadPreview = safePayloadPreview(event.payload);

  return (
    <li className="relative rounded-md border border-border/70 bg-background/55 p-3 pl-5 before:absolute before:left-2 before:top-4 before:h-2 before:w-2 before:rounded-full before:bg-primary before:shadow-[0_0_14px_hsl(var(--primary)/0.55)]">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium">{event.event_type}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {event.source === "live" ? "Live stream" : "Persisted backlog"}
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          {formatDate(event.created_at)}
        </p>
      </div>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        {event.message ?? event.status ?? "Workflow event"}
      </p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
        {event.stage ? <span>Stage: {event.stage}</span> : null}
        {event.status ? <span>Status: {event.status}</span> : null}
      </div>
      {payloadPreview ? (
        <pre className="ops-code mt-3 max-h-40">
          {payloadPreview}
        </pre>
      ) : null}
    </li>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
