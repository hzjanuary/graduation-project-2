import React, { act, type ReactElement } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { KnowledgeDocumentList } from "@/components/knowledge/knowledge-document-list";
import { KnowledgeSearchPanel } from "@/components/knowledge/knowledge-search-panel";
import {
  extractWorkflowEvidence,
  WorkflowEvidencePanel,
} from "@/components/workflows/workflow-evidence-panel";
import type {
  WorkflowEvent,
  WorkflowEvidenceCitation,
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
  vi.restoreAllMocks();
});

describe("workflow evidence UI", () => {
  it("renders an honest empty state without fake citations", async () => {
    await render(<WorkflowEvidencePanel workflow={sampleWorkflow()} />);

    expect(document.body.textContent).toContain(
      "No retrieved evidence has been attached yet.",
    );
    expect(document.body.textContent).not.toContain("Demo citation");
  });

  it("renders runtime_context.rag citations grouped by stage", async () => {
    await render(
      <WorkflowEvidencePanel
        workflow={{
          ...sampleWorkflow(),
          runtime_context: {
            rag: {
              enabled: true,
              stages: {
                compliance: {
                  citations: [sampleCitation("compliance")],
                },
              },
            },
          },
        }}
      />,
    );

    expect(document.body.textContent).toContain("Compliance");
    expect(document.body.textContent).toContain("Procurement Policy");
    expect(document.body.textContent).toContain("POL-1 section 4");
    expect(document.body.textContent).toContain("Score 82%");
  });

  it("renders outputs and stage_outputs evidence", async () => {
    const workflow = {
      ...sampleWorkflow(),
      outputs: {
        evidence: {
          approval: [sampleCitation("approval", "approval-citation")],
        },
      },
      stage_outputs: {
        validation: {
          evidence: [sampleCitation("validation", "validation-citation")],
        },
      },
    };

    await render(<WorkflowEvidencePanel workflow={workflow} />);

    expect(document.body.textContent).toContain("Approval package");
    expect(document.body.textContent).toContain("Validation and finance");
    expect(document.body.textContent).toContain("approval-citation");
    expect(document.body.textContent).toContain("validation-citation");
  });

  it("extracts citations from grounding events only when citation objects exist", () => {
    const events: WorkflowEvent[] = [
      {
        event_id: "event-1",
        workflow_id: "workflow-1",
        event_type: "knowledge.grounding.completed",
        payload: {
          stage: "approval",
          citations: [sampleCitation("approval")],
          citation_ids: ["not-enough-to-render"],
        },
        created_at: "2026-07-13T10:00:00Z",
      },
      {
        event_id: "event-2",
        workflow_id: "workflow-1",
        event_type: "knowledge.grounding.completed",
        payload: { stage: "compliance", citation_ids: ["summary-only"] },
        created_at: "2026-07-13T10:01:00Z",
      },
    ];

    const citations = extractWorkflowEvidence(sampleWorkflow(), events);

    expect(citations).toHaveLength(1);
    expect(citations[0].stage).toBe("approval");
  });

  it("does not render raw embeddings, vector payloads, or prompt fields", async () => {
    await render(
      <WorkflowEvidencePanel
        workflow={{
          ...sampleWorkflow(),
          outputs: {
            evidence: {
              compliance: [
                {
                  ...sampleCitation("compliance"),
                  raw_prompt: "hidden prompt",
                  embedding_vector: [0.1, 0.2],
                  provider_payload: { unsafe: true },
                },
              ],
            },
          },
        }}
      />,
    );

    expect(document.body.textContent).toContain(
      "No retrieved evidence has been attached yet.",
    );
    expect(document.body.textContent).not.toContain("hidden prompt");
    expect(document.body.textContent).not.toContain("0.1");
  });

  it("bounds long excerpts in the rendered panel", async () => {
    const longCitation = {
      ...sampleCitation("compliance"),
      excerpt: "Evidence ".repeat(200),
    };

    await render(
      <WorkflowEvidencePanel
        workflow={{
          ...sampleWorkflow(),
          outputs: { evidence: { compliance: [longCitation] } },
        }}
      />,
    );

    expect(document.body.textContent).toContain("Evidence Evidence");
    expect(document.body.textContent).toContain("...");
  });
});

describe("knowledge search and catalog UI", () => {
  it("renders knowledge search success and empty states", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        query: "procurement policy",
        results: [
          {
            chunk_id: "chunk-1",
            document_id: "demo-kb-procurement-policy",
            chunk_text: "Bounded policy evidence.",
            score: 0.91,
            source_type: "policy",
            document_title: "Procurement Policy",
            domain: "procurement",
            citation: sampleCitation("compliance"),
            metadata: {},
          },
        ],
      }),
    );

    await render(<KnowledgeSearchPanel token="access-token" />);
    await clickButton("Search");

    expect(fetchSpy.mock.calls[0][0]).toBe(
      "http://localhost:8000/api/v1/knowledge/search",
    );
    expect(document.body.textContent).toContain("Procurement Policy");
    expect(document.body.textContent).toContain("Score 91%");

    act(() => {
      root?.unmount();
    });
    root = null;
    container?.remove();
    container = null;

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ query: "missing", results: [] }),
    );

    await render(<KnowledgeSearchPanel token="access-token" />);
    await clickButton("Search");

    expect(document.body.textContent).toContain(
      "No knowledge results matched that query.",
    );
  });

  it("shows knowledge search 403 and 503 errors clearly", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: { message: "Forbidden" } }, 403, "Forbidden"),
    );

    await render(<KnowledgeSearchPanel token="access-token" />);
    await clickButton("Search");

    expect(document.body.textContent).toContain(
      "Your account cannot search the knowledge base.",
    );

    act(() => {
      root?.unmount();
    });
    root = null;
    container?.remove();
    container = null;

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        { detail: { message: "Knowledge retrieval provider is unavailable." } },
        503,
        "Service Unavailable",
      ),
    );

    await render(<KnowledgeSearchPanel token="access-token" />);
    await clickButton("Search");

    expect(document.body.textContent).toContain(
      "Knowledge retrieval is unavailable.",
    );
  });

  it("renders document catalog metadata", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        documents: [sampleDocument()],
        count: 1,
      }),
    );

    await render(<KnowledgeDocumentList token="access-token" />);

    expect(document.body.textContent).toContain("Procurement Policy");
    expect(document.body.textContent).toContain("policy / procurement");
    expect(document.body.textContent).toContain("ID: demo-kb-procurement-policy");
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

function sampleWorkflow(): WorkflowState {
  return {
    workflow_id: "workflow-1",
    workflow_type: "procurement_quotation",
    domain: "it_equipment",
    status: "WAITING_APPROVAL",
    request: { raw_text: "Need laptops" },
    metadata: {},
    current_step: "approval",
    retry_count: 0,
    created_at: "2026-07-13T10:00:00Z",
    updated_at: "2026-07-13T10:00:00Z",
  };
}

function sampleCitation(
  stage: string,
  citationId = "citation-demo-1",
): WorkflowEvidenceCitation {
  return {
    citation_id: citationId,
    document_id: "demo-kb-procurement-policy",
    document_title: "Procurement Policy",
    source_type: "policy",
    section: "POL-1 section 4",
    page: 2,
    excerpt: "Policy requires manager approval for discounted laptop purchases.",
    relevance_score: 0.82,
    citation_label:
      citationId === "citation-demo-1" ? "POL-1 section 4" : citationId,
    stage,
    reason: "compliance_policy_contract_checklist",
  };
}

function sampleDocument() {
  return {
    document_id: "demo-kb-procurement-policy",
    title: "Procurement Policy",
    source_type: "policy",
    domain: "procurement",
    version: "2026.1",
    effective_date: "2026-01-01",
    owner_team: "Procurement",
    object_storage_key: "demo/knowledge/demo-kb-procurement-policy.txt",
    checksum: "abc123",
    content_type: "text/plain",
    dataset_path: "datasets/policies/POLICY-DISCOUNT-APPROVAL.md",
    tags: ["demo"],
    attributes: {},
  };
}
