import { describe, expect, it, vi } from "vitest";

import {
  getKnowledgeDocument,
  listKnowledgeDocuments,
  searchKnowledge,
} from "@/lib/api/knowledge";

describe("knowledge API client", () => {
  it("searches knowledge with bearer auth and request body", async () => {
    const payload = {
      query: "procurement policy approval evidence",
      top_k: 3,
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({ query: payload.query, results: [] }),
    );

    await searchKnowledge(payload, {
      token: "access-token",
      baseUrl: "http://api.test/api/v1",
      fetcher,
    });

    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("http://api.test/api/v1/knowledge/search");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify(payload));
    expect(new Headers(init?.headers).get("Authorization")).toBe(
      "Bearer access-token",
    );
  });

  it("lists knowledge documents with bearer auth", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({ documents: [], count: 0 }),
    );

    await listKnowledgeDocuments({
      token: "access-token",
      baseUrl: "http://api.test/api/v1",
      fetcher,
    });

    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("http://api.test/api/v1/knowledge/documents");
    expect(new Headers(init?.headers).get("Authorization")).toBe(
      "Bearer access-token",
    );
  });

  it("loads one encoded knowledge document id", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({
        document: sampleDocument("demo policy/id"),
        content_preview: "Policy preview",
      }),
    );

    await getKnowledgeDocument("demo policy/id", {
      token: "access-token",
      baseUrl: "http://api.test/api/v1",
      fetcher,
    });

    expect(fetcher.mock.calls[0][0]).toBe(
      "http://api.test/api/v1/knowledge/documents/demo%20policy%2Fid",
    );
  });
});

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function sampleDocument(documentId: string) {
  return {
    document_id: documentId,
    title: "Procurement Policy",
    source_type: "policy",
    domain: "procurement",
    version: "2026.1",
    effective_date: "2026-01-01",
    owner_team: "Procurement",
    object_storage_key: "demo/knowledge/policy.txt",
    checksum: "abc123",
    content_type: "text/plain",
    dataset_path: "datasets/policies/POLICY.md",
    tags: ["demo"],
    attributes: {},
  };
}
