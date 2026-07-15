import React, { act, type ReactElement } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorkflowApprovalHistory } from "@/components/workflows/workflow-approval-history";
import { WorkflowApprovalPanel } from "@/components/workflows/workflow-approval-panel";
import { ACCESS_TOKEN_STORAGE_KEY } from "@/lib/auth/session";
import type {
  ApprovalHistoryResponse,
  ApprovalRecord,
  WorkflowState,
} from "@/lib/api/types";

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

describe("workflow approval UI", () => {
  it("renders approval actions for waiting approval workflows", async () => {
    await render(
      <WorkflowApprovalPanel
        approvalHistory={emptyHistory("workflow-1")}
        workflow={sampleWorkflow("workflow-1", "WAITING_APPROVAL")}
      />,
    );

    expect(document.body.textContent).toContain("Approve");
    expect(document.body.textContent).toContain("Reject");
    expect(document.body.textContent).toContain("Request changes");
  });

  it("requires a reject comment before calling the API", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    await render(
      <WorkflowApprovalPanel
        approvalHistory={emptyHistory("workflow-1")}
        workflow={sampleWorkflow("workflow-1", "WAITING_APPROVAL")}
      />,
    );

    await clickButton("Reject");

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain(
      "Reject decisions require a comment.",
    );
  });

  it("submits approve decisions and triggers refresh", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    const onApprovalChanged = vi.fn();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        workflow_id: "workflow-1",
        approval: sampleApproval("approve"),
        previous_status: "WAITING_APPROVAL",
        next_status: "APPROVED",
        can_resume: true,
        resume_recommended: true,
      }),
    );

    await render(
      <WorkflowApprovalPanel
        approvalHistory={emptyHistory("workflow-1")}
        workflow={sampleWorkflow("workflow-1", "WAITING_APPROVAL")}
        onApprovalChanged={onApprovalChanged}
      />,
    );

    setTextareaValue("approvalComment", "Approved for customer response.");
    await clickButton("Approve");

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/v1/workflows/workflow-1/approval");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toMatchObject({
      decision: "approve",
      comment: "Approved for customer response.",
    });
    expect(onApprovalChanged).toHaveBeenCalledTimes(1);
    expect(document.body.textContent).toContain(
      "Workflow approved. It is ready for explicit resume.",
    );
  });

  it("submits request changes decisions", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        workflow_id: "workflow-1",
        approval: sampleApproval("request_changes"),
        previous_status: "WAITING_APPROVAL",
        next_status: "WAITING_APPROVAL",
        can_resume: false,
        resume_recommended: false,
      }),
    );

    await render(
      <WorkflowApprovalPanel
        approvalHistory={emptyHistory("workflow-1")}
        workflow={sampleWorkflow("workflow-1", "WAITING_APPROVAL")}
      />,
    );

    await clickButton("Request changes");

    expect(JSON.parse(String(fetchSpy.mock.calls[0][1]?.body))).toMatchObject({
      decision: "request_changes",
      comment: null,
    });
    expect(document.body.textContent).toContain(
      "Changes requested. The workflow remains in approval review.",
    );
  });

  it("shows forbidden approval errors from the backend", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          detail: {
            code: "approval_forbidden",
            message: "Insufficient permissions for approval decision.",
          },
        },
        403,
        "Forbidden",
      ),
    );

    await render(
      <WorkflowApprovalPanel
        approvalHistory={emptyHistory("workflow-1")}
        workflow={sampleWorkflow("workflow-1", "WAITING_APPROVAL")}
      />,
    );

    await clickButton("Approve");

    expect(document.body.textContent).toContain(
      "Your account cannot submit approval decisions.",
    );
  });

  it("shows conflict approval errors from the backend", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          detail: {
            code: "approval_duplicate_final_decision",
            message: "A final approval decision already exists.",
          },
        },
        409,
        "Conflict",
      ),
    );

    await render(
      <WorkflowApprovalPanel
        approvalHistory={emptyHistory("workflow-1")}
        workflow={sampleWorkflow("workflow-1", "WAITING_APPROVAL")}
      />,
    );

    await clickButton("Approve");

    expect(document.body.textContent).toContain(
      "A final approval decision already exists.",
    );
  });

  it("renders empty and populated approval history", async () => {
    await render(<WorkflowApprovalHistory history={emptyHistory("workflow-1")} />);

    expect(document.body.textContent).toContain(
      "No approval decisions have been recorded",
    );

    act(() => {
      root?.unmount();
    });
    root = null;
    container?.remove();
    container = null;

    await render(
      <WorkflowApprovalHistory
        history={{
          workflow_id: "workflow-1",
          approvals: [sampleApproval("approve")],
          has_final_decision: true,
          can_resume: true,
        }}
      />,
    );

    expect(document.body.textContent).toContain("Approved");
    expect(document.body.textContent).toContain("manager@example.test");
    expect(document.body.textContent).toContain("Previous: WAITING_APPROVAL");
    expect(document.body.textContent).toContain("Next: APPROVED");
  });

  it("resumes approved workflows through the resume endpoint", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    const onApprovalChanged = vi.fn();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        workflow_id: "workflow-1",
        previous_status: "APPROVED",
        next_status: "COMPLETED",
        resumed: true,
        message: "Workflow resume completed.",
        request_id: null,
      }),
    );

    await render(
      <WorkflowApprovalPanel
        approvalHistory={{
          ...emptyHistory("workflow-1"),
          can_resume: true,
        }}
        workflow={sampleWorkflow("workflow-1", "APPROVED")}
        onApprovalChanged={onApprovalChanged}
      />,
    );

    await clickButton("Resume workflow");

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/v1/workflows/workflow-1/resume");
    expect(url).not.toContain("/run");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({}));
    expect(onApprovalChanged).toHaveBeenCalledTimes(1);
    expect(document.body.textContent).toContain("Workflow resume completed.");
  });

  it("shows resume conflict errors", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          detail: {
            code: "workflow_resume_not_allowed",
            message: "Workflow cannot resume without approval.",
          },
        },
        409,
        "Conflict",
      ),
    );

    await render(
      <WorkflowApprovalPanel
        approvalHistory={{
          ...emptyHistory("workflow-1"),
          can_resume: true,
        }}
        workflow={sampleWorkflow("workflow-1", "APPROVED")}
      />,
    );

    await clickButton("Resume workflow");

    expect(document.body.textContent).toContain(
      "Workflow cannot resume without approval.",
    );
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

function setTextareaValue(name: string, value: string) {
  const input = document.querySelector(`[name="${name}"]`) as
    | HTMLTextAreaElement
    | null;
  if (!input) {
    throw new Error(`Expected textarea ${name} to exist`);
  }
  const valueSetter = Object.getOwnPropertyDescriptor(
    HTMLTextAreaElement.prototype,
    "value",
  )?.set;
  act(() => {
    valueSetter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
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

function emptyHistory(workflowId: string): ApprovalHistoryResponse {
  return {
    workflow_id: workflowId,
    approvals: [],
    has_final_decision: false,
    can_resume: false,
  };
}

function sampleWorkflow(
  workflowId: string,
  status: WorkflowState["status"],
): WorkflowState {
  return {
    workflow_id: workflowId,
    workflow_type: "procurement_quotation",
    domain: "it_equipment",
    status,
    request: { raw_text: "Need laptops" },
    metadata: {},
    current_step: "approval",
    retry_count: 0,
    created_at: "2026-07-13T10:00:00Z",
    updated_at: "2026-07-13T10:00:00Z",
  };
}

function sampleApproval(
  decision: "approve" | "reject" | "request_changes",
): ApprovalRecord {
  return {
    decision_id: "approval-1",
    workflow_id: "workflow-1",
    decision,
    actor_id: "user-1",
    actor_email: "manager@example.test",
    actor_roles: ["Manager"],
    comment: "Approved for customer response.",
    decided_at: "2026-07-13T10:03:00Z",
    previous_status: "WAITING_APPROVAL",
    next_status: decision === "approve" ? "APPROVED" : "WAITING_APPROVAL",
    request_id: null,
    metadata: {},
  };
}
