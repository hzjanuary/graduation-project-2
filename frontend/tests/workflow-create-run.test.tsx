import React, { act, type ReactElement } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildWorkflowCreateRequest,
  WorkflowCreateForm,
  WorkflowCreateFormValidationError,
} from "@/components/workflows/workflow-create-form";
import { WorkflowNextStepGuide } from "@/components/workflows/workflow-next-step-guide";
import { WorkflowRunPanel } from "@/components/workflows/workflow-run-panel";
import { ACCESS_TOKEN_STORAGE_KEY } from "@/lib/auth/session";

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
});

describe("workflow create and run actions", () => {
  it("builds a backend-compatible create request", () => {
    const payload = buildWorkflowCreateRequest({
      domain: "it_equipment",
      customerName: "Acme Manufacturing Group",
      rawText: "Need 50 laptops",
      itemsJson: '[{"name":"Laptop","quantity":50}]',
      metadataJson: '{"tags":{"priority":"demo"},"attributes":{"source":"rfq"}}',
    });

    expect(payload).toEqual({
      workflow_type: "procurement_quotation",
      domain: "it_equipment",
      request: {
        raw_text: "Need 50 laptops",
        source: "manual_text",
        customer: { name: "Acme Manufacturing Group" },
        items: [{ name: "Laptop", quantity: 50 }],
      },
      metadata: {
        state_version: 1,
        tags: { priority: "demo" },
        attributes: { source: "rfq" },
      },
    });
  });

  it("rejects invalid create form JSON before calling the API", () => {
    expect(() =>
      buildWorkflowCreateRequest({
        domain: "it_equipment",
        customerName: "",
        rawText: "Need laptops",
        itemsJson: "{not-json}",
        metadataJson: "{}",
      }),
    ).toThrow(WorkflowCreateFormValidationError);
  });

  it("submits the create form and shows a detail link", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ workflow: sampleWorkflow("workflow-created") }),
    );

    await render(<WorkflowCreateForm />);
    setInputValue("rawText", "Need 50 standard laptops");

    await submitForm();

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/workflows",
      expect.objectContaining({
        method: "POST",
      }),
    );
    const init = fetchSpy.mock.calls[0][1];
    expect(new Headers(init?.headers).get("Authorization")).toBe(
      "Bearer access-token",
    );
    expect(document.body.textContent).toContain("Workflow created.");
    expect(document.body.textContent).toContain("workflow-created");
  });

  it("shows create API errors without fake success data", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "Forbidden" }, 403, "Forbidden"),
    );

    await render(<WorkflowCreateForm />);
    setInputValue("rawText", "Need 50 standard laptops");

    await submitForm();

    expect(document.body.textContent).toContain(
      "Your account cannot create workflows.",
    );
    expect(document.body.textContent).not.toContain("Workflow created.");
  });

  it("runs a workflow and displays the runtime result", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    const onRunCompleted = vi.fn();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(sampleRunResponse("workflow-1")),
    );

    await render(
      <WorkflowRunPanel
        workflowId="workflow-1"
        onRunCompleted={onRunCompleted}
      />,
    );

    await clickButton("Run workflow");

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/workflows/workflow-1/run",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(onRunCompleted).toHaveBeenCalledTimes(1);
    expect(document.body.textContent).toContain("WAITING_APPROVAL");
    expect(document.body.textContent).toContain("planner, retrieval, quotation");
  });

  it("shows runtime conflict errors from the backend", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          detail: {
            code: "workflow_runtime_precondition_failed",
            message: "Workflow cannot run from WAITING_APPROVAL",
          },
        },
        409,
        "Conflict",
      ),
    );

    await render(<WorkflowRunPanel workflowId="workflow-1" />);

    await clickButton("Run workflow");

    expect(document.body.textContent).toContain(
      "Workflow cannot run from WAITING_APPROVAL",
    );
  });

  it("does not encourage rerun after runtime stops at approval", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    await render(
      <WorkflowRunPanel
        workflowId="workflow-1"
        workflowStatus="WAITING_APPROVAL"
      />,
    );

    expect(document.body.textContent).toContain("Run already stopped at approval");
    expect(document.body.textContent).toContain("Review and approve");
    expect(document.body.textContent).not.toContain("Run workflow");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it.each([
    ["CREATED", "This workflow has not run yet."],
    ["WAITING_APPROVAL", "Runtime has stopped at the human approval boundary."],
    ["APPROVED", "Approval is complete; continuation is ready."],
    ["COMPLETED", "Workflow is complete."],
  ] as const)("renders next-step guide for %s", async (status, expectedText) => {
    await render(<WorkflowNextStepGuide status={status} />);

    expect(document.body.textContent).toContain(expectedText);
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

async function submitForm() {
  const form = document.querySelector("form");
  if (!form) {
    throw new Error("Expected form to exist");
  }
  await act(async () => {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
  await flushEffects();
}

async function clickButton(label: string) {
  const button = Array.from(document.querySelectorAll("button")).find(
    (candidate) => candidate.textContent === label,
  );
  if (!button) {
    throw new Error(`Expected button ${label} to exist`);
  }
  await act(async () => {
    button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
  await flushEffects();
}

async function flushEffects() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function setInputValue(name: string, value: string) {
  const input = document.querySelector(`[name="${name}"]`) as
    | HTMLInputElement
    | HTMLTextAreaElement
    | null;
  if (!input) {
    throw new Error(`Expected input ${name} to exist`);
  }
  input.value = value;
}

function jsonResponse(
  payload: unknown,
  status = 200,
  statusText = "OK",
): Response {
  return new Response(JSON.stringify(payload), {
    status,
    statusText,
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
    metadata: { state_version: 1 },
    current_step: null,
    retry_count: 0,
    created_at: "2026-07-13T10:00:00Z",
    updated_at: "2026-07-13T10:00:00Z",
  };
}

function sampleRunResponse(workflowId: string) {
  return {
    result: {
      state: {
        ...sampleWorkflow(workflowId),
        status: "WAITING_APPROVAL",
        completed_stages: ["planner", "retrieval", "quotation"],
      },
      completed: false,
      failed: false,
      message: "Runtime stopped at waiting approval",
    },
    workflow_id: workflowId,
    status: "WAITING_APPROVAL",
    completed_stages: ["planner", "retrieval", "quotation"],
    waiting_for_approval: true,
    completed: false,
    failed: false,
    message: "Runtime stopped at waiting approval",
  };
}
