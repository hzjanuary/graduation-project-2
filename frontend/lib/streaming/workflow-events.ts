import { getWsBaseUrl } from "@/lib/config";
import type {
  WorkflowEvent,
  WorkflowEventStreamMessage,
  WorkflowTimelineEvent,
} from "@/lib/api/types";

const WORKFLOW_EVENT_MESSAGE_TYPE = "workflow.event";
const UNSAFE_PAYLOAD_KEY_PARTS = [
  "_sa_",
  "authorization",
  "password",
  "request_payload",
  "secret",
  "state_payload",
  "token",
];

export function buildWorkflowEventStreamUrl(
  workflowId: string,
  accessToken: string,
  baseUrl = getWsBaseUrl(),
): string {
  const url = new URL(
    `${baseUrl}/workflows/${encodeURIComponent(workflowId)}/stream`,
  );
  url.searchParams.set("access_token", accessToken);
  return url.toString();
}

export function parseWorkflowEventStreamMessage(
  data: string,
): WorkflowEventStreamMessage | null {
  try {
    const parsed = JSON.parse(data) as unknown;
    if (!isWorkflowEventStreamMessage(parsed)) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function workflowEventToTimelineEvent(
  event: WorkflowEvent,
): WorkflowTimelineEvent {
  return {
    event_id: event.event_id,
    workflow_id: event.workflow_id,
    event_type: event.event_type,
    status: event.status,
    stage: event.agent_name ?? stageFromPayload(event.payload),
    message: event.message,
    created_at: event.created_at,
    payload: sanitizeTimelinePayload(event.payload),
    source: "persisted",
  };
}

export function streamMessageToTimelineEvent(
  message: WorkflowEventStreamMessage,
): WorkflowTimelineEvent {
  return {
    event_id: message.event_id,
    workflow_id: message.workflow_id,
    event_type: message.event_type,
    status: message.status,
    stage: message.stage,
    message: message.message,
    created_at: message.created_at,
    emitted_at: message.emitted_at,
    sequence: message.sequence,
    payload: sanitizeTimelinePayload(message.payload),
    source: "live",
  };
}

export function mergeWorkflowTimelineEvents(
  persistedEvents: WorkflowEvent[],
  liveMessages: WorkflowEventStreamMessage[],
): WorkflowTimelineEvent[] {
  const byEventId = new Map<string, WorkflowTimelineEvent>();

  for (const event of persistedEvents) {
    byEventId.set(event.event_id, workflowEventToTimelineEvent(event));
  }
  for (const message of liveMessages) {
    byEventId.set(message.event_id, streamMessageToTimelineEvent(message));
  }

  return Array.from(byEventId.values()).sort(compareTimelineEvents);
}

export function safePayloadPreview(payload: Record<string, unknown>): string | null {
  const sanitized = sanitizeTimelinePayload(payload);
  if (Object.keys(sanitized).length === 0) {
    return null;
  }
  return JSON.stringify(sanitized, null, 2);
}

function isWorkflowEventStreamMessage(
  value: unknown,
): value is WorkflowEventStreamMessage {
  if (!isRecord(value)) {
    return false;
  }
  return (
    value.type === WORKFLOW_EVENT_MESSAGE_TYPE &&
    typeof value.workflow_id === "string" &&
    typeof value.event_id === "string" &&
    typeof value.event_type === "string" &&
    typeof value.created_at === "string" &&
    typeof value.emitted_at === "string" &&
    isRecord(value.payload)
  );
}

function compareTimelineEvents(
  first: WorkflowTimelineEvent,
  second: WorkflowTimelineEvent,
): number {
  const firstTime = new Date(first.created_at).getTime();
  const secondTime = new Date(second.created_at).getTime();
  if (firstTime !== secondTime) {
    return firstTime - secondTime;
  }

  const firstEmitted = first.emitted_at
    ? new Date(first.emitted_at).getTime()
    : firstTime;
  const secondEmitted = second.emitted_at
    ? new Date(second.emitted_at).getTime()
    : secondTime;
  if (firstEmitted !== secondEmitted) {
    return firstEmitted - secondEmitted;
  }

  return first.event_id.localeCompare(second.event_id);
}

function sanitizeTimelinePayload(
  payload: Record<string, unknown>,
): Record<string, unknown> {
  const sanitized: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(payload).slice(0, 20)) {
    if (isUnsafePayloadKey(key)) {
      continue;
    }
    sanitized[key] = sanitizeValue(value);
  }
  return sanitized;
}

function sanitizeValue(value: unknown): unknown {
  if (
    value === null ||
    typeof value === "boolean" ||
    typeof value === "number"
  ) {
    return value;
  }
  if (typeof value === "string") {
    return value.slice(0, 300);
  }
  if (Array.isArray(value)) {
    return value.slice(0, 10).map(sanitizeValue);
  }
  if (isRecord(value)) {
    return sanitizeTimelinePayload(value);
  }
  return String(value).slice(0, 300);
}

function stageFromPayload(payload: Record<string, unknown>): string | null {
  return typeof payload.stage === "string" ? payload.stage : null;
}

function isUnsafePayloadKey(key: string): boolean {
  const normalizedKey = key.toLowerCase();
  return UNSAFE_PAYLOAD_KEY_PARTS.some((part) => normalizedKey.includes(part));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
