import React, { act, type ReactElement } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorkflowEventTimeline } from "@/components/workflows/workflow-event-timeline";
import {
  buildWorkflowEventStreamUrl,
  mergeWorkflowTimelineEvents,
  parseWorkflowEventStreamMessage,
} from "@/lib/streaming/workflow-events";
import { ACCESS_TOKEN_STORAGE_KEY } from "@/lib/auth/session";
import type { WorkflowEvent, WorkflowEventStreamMessage } from "@/lib/api/types";

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) {
    act(() => {
      root?.unmount();
    });
  }
  root = null;
  container?.remove();
  container = null;
  window.localStorage.clear();
  vi.restoreAllMocks();
  MockWebSocket.instances = [];
});

describe("workflow event stream", () => {
  it("builds a workflow-scoped WebSocket URL with query token auth", () => {
    expect(
      buildWorkflowEventStreamUrl(
        "workflow/one",
        "access token",
        "ws://api.test/api/v1",
      ),
    ).toBe(
      "ws://api.test/api/v1/workflows/workflow%2Fone/stream?access_token=access+token",
    );
  });

  it("parses valid messages and rejects malformed messages", () => {
    const message = sampleStreamMessage("event-1", "workflow.node.completed");

    expect(
      parseWorkflowEventStreamMessage(JSON.stringify(message)),
    ).toMatchObject({
      event_id: "event-1",
      event_type: "workflow.node.completed",
    });
    expect(parseWorkflowEventStreamMessage("not-json")).toBeNull();
    expect(parseWorkflowEventStreamMessage(JSON.stringify({ type: "other" }))).toBeNull();
  });

  it("deduplicates persisted and live events by event_id", () => {
    const events = mergeWorkflowTimelineEvents(
      [samplePersistedEvent("event-1", "Persisted message")],
      [sampleStreamMessage("event-1", "workflow.node.completed")],
    );

    expect(events).toHaveLength(1);
    expect(events[0].source).toBe("live");
    expect(events[0].event_type).toBe("workflow.node.completed");
  });

  it("does not connect when no access token exists", async () => {
    installMockWebSocket();

    await render(
      <WorkflowEventTimeline
        persistedEvents={[]}
        workflowId="workflow-1"
      />,
    );

    expect(MockWebSocket.instances).toHaveLength(0);
    expect(document.body.textContent).toContain("Stream disconnected");
    expect(document.body.textContent).toContain(
      "Sign in to open the workflow event stream.",
    );
  });

  it("renders connection state, backlog, live messages, and malformed errors", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    installMockWebSocket();

    await render(
      <WorkflowEventTimeline
        persistedEvents={[samplePersistedEvent("event-1", "Runtime started")]}
        workflowId="workflow-1"
      />,
    );

    expect(MockWebSocket.instances[0].url).toBe(
      "ws://localhost:8000/api/v1/workflows/workflow-1/stream?access_token=access-token",
    );
    expect(document.body.textContent).toContain("Stream connecting");
    expect(document.body.textContent).toContain("Runtime started");

    await act(async () => {
      MockWebSocket.instances[0].emitOpen();
    });
    expect(document.body.textContent).toContain("Stream connected");

    await act(async () => {
      MockWebSocket.instances[0].emitMessage(
        JSON.stringify(sampleStreamMessage("event-2", "workflow.node.completed")),
      );
    });
    expect(document.body.textContent).toContain("Stage completed");
    expect(document.body.textContent).toContain("Live stream");

    await act(async () => {
      MockWebSocket.instances[0].emitMessage("{malformed");
    });
    expect(document.body.textContent).toContain(
      "Received an invalid workflow stream message.",
    );
  });

  it("closes the socket on unmount", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    installMockWebSocket();

    await render(
      <WorkflowEventTimeline
        persistedEvents={[]}
        workflowId="workflow-1"
      />,
    );

    const socket = MockWebSocket.instances[0];
    act(() => {
      root?.unmount();
    });

    expect(socket.close).toHaveBeenCalledTimes(1);
  });
});

async function render(element: ReactElement) {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root?.render(element);
  });
  await flushEffects();
}

async function flushEffects() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function installMockWebSocket() {
  vi.stubGlobal("WebSocket", MockWebSocket);
}

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  readonly url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  emitOpen() {
    this.onopen?.();
  }

  emitMessage(data: string) {
    this.onmessage?.({ data });
  }
}

function samplePersistedEvent(
  eventId: string,
  message: string,
): WorkflowEvent {
  return {
    event_id: eventId,
    workflow_id: "workflow-1",
    event_type: "workflow.runtime.started",
    agent_name: "planner",
    status: "completed",
    message,
    payload: {
      stage: "planner",
      token: "should-not-render",
      request_payload: { raw_text: "hidden" },
    },
    created_at: "2026-07-13T10:01:00Z",
  };
}

function sampleStreamMessage(
  eventId: string,
  eventType: string,
): WorkflowEventStreamMessage {
  return {
    type: "workflow.event",
    workflow_id: "workflow-1",
    event_id: eventId,
    event_type: eventType,
    status: "completed",
    stage: "retrieval",
    message: "Stage completed",
    created_at: "2026-07-13T10:02:00Z",
    emitted_at: "2026-07-13T10:02:01Z",
    sequence: 1,
    payload: { stage: "retrieval", workflow_status: "RETRIEVING" },
  };
}
