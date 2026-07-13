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
    <section className="rounded-lg border bg-card p-5 text-card-foreground shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">
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
            className="inline-flex h-9 items-center justify-center rounded-md border px-3 text-sm font-medium hover:bg-muted"
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
    <span className="inline-flex h-9 items-center rounded-full border px-3 text-xs font-medium text-muted-foreground">
      {label}
    </span>
  );
}

function TimelineItem({ event }: { event: WorkflowTimelineEvent }) {
  const payloadPreview = safePayloadPreview(event.payload);

  return (
    <li className="rounded-md border bg-background p-3">
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
        <pre className="mt-3 max-h-40 overflow-auto rounded-md bg-muted p-3 text-xs leading-5 text-muted-foreground">
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
