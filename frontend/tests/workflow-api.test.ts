import { describe, expect, it, vi } from "vitest";

import {
  createWorkflow,
  getWorkflow,
  listWorkflowEvents,
  listWorkflows,
  runWorkflow,
} from "@/lib/api/workflows";
import type { WorkflowCreateRequest } from "@/lib/api/types";

describe("workflow API client", () => {
  it("lists workflows with bearer auth and pagination params", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({ workflows: [], count: 0, limit: 25, offset: 5, status: null }),
    );

    await listWorkflows(
      { token: "access-token", baseUrl: "http://api.test/api/v1", fetcher },
      { limit: 25, offset: 5 },
    );

    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("http://api.test/api/v1/workflows?limit=25&offset=5");
    expect(new Headers(init?.headers).get("Authorization")).toBe(
      "Bearer access-token",
    );
  });

  it("loads one workflow by id", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({ workflow: sampleWorkflow("workflow-1") }),
    );

    await getWorkflow("workflow-1", {
      token: "access-token",
      baseUrl: "http://api.test/api/v1",
      fetcher,
    });

    expect(fetcher.mock.calls[0][0]).toBe(
      "http://api.test/api/v1/workflows/workflow-1",
    );
  });

  it("loads persisted workflow events", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({ events: [], count: 0, limit: 10, offset: 0 }),
    );

    await listWorkflowEvents(
      "workflow-1",
      { token: "access-token", baseUrl: "http://api.test/api/v1", fetcher },
      { limit: 10, offset: 0 },
    );

    expect(fetcher.mock.calls[0][0]).toBe(
      "http://api.test/api/v1/workflows/workflow-1/events?limit=10&offset=0",
    );
  });

  it("creates a workflow with the backend request shape", async () => {
    const payload: WorkflowCreateRequest = {
      workflow_type: "procurement_quotation",
      domain: "it_equipment",
      request: { raw_text: "Need laptops", items: [] },
      metadata: { state_version: 1 },
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({ workflow: sampleWorkflow("workflow-1") }),
    );

    await createWorkflow(payload, {
      token: "access-token",
      baseUrl: "http://api.test/api/v1",
      fetcher,
    });

    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("http://api.test/api/v1/workflows");
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("Authorization")).toBe(
      "Bearer access-token",
    );
    expect(init?.body).toBe(JSON.stringify(payload));
  });

  it("runs a workflow without sending a request body", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({
        result: {
          state: sampleWorkflow("workflow-1"),
          completed: false,
          failed: false,
          message: "Waiting for approval",
        },
        workflow_id: "workflow-1",
        status: "WAITING_APPROVAL",
        completed_stages: ["planner", "retrieval"],
        waiting_for_approval: true,
        completed: false,
        failed: false,
        message: "Waiting for approval",
      }),
    );

    await runWorkflow("workflow-1", {
      token: "access-token",
      baseUrl: "http://api.test/api/v1",
      fetcher,
    });

    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("http://api.test/api/v1/workflows/workflow-1/run");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBeUndefined();
    expect(new Headers(init?.headers).get("Authorization")).toBe(
      "Bearer access-token",
    );
  });
});

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function sampleWorkflow(workflowId: string) {
  return {
    workflow_id: workflowId,
    workflow_type: "procurement_quotation",
    domain: "it_equipment",
    status: "CREATED",
    request: { raw_text: "Need laptops" },
    metadata: {},
    current_step: null,
    retry_count: 0,
    created_at: "2026-07-13T10:00:00Z",
    updated_at: "2026-07-13T10:00:00Z",
  };
}
