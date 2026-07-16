import { apiFetch, type ApiFetchOptions } from "@/lib/api/client";
import type {
  KnowledgeDocumentDetailResponse,
  KnowledgeDocumentListResponse,
  KnowledgeSearchRequest,
  KnowledgeSearchResponse,
} from "@/lib/api/types";

type KnowledgeRequestOptions = Pick<ApiFetchOptions, "baseUrl" | "fetcher"> & {
  token: string;
};

export function searchKnowledge(
  payload: KnowledgeSearchRequest,
  options: KnowledgeRequestOptions,
): Promise<KnowledgeSearchResponse> {
  return apiFetch<KnowledgeSearchResponse>("/knowledge/search", {
    ...options,
    method: "POST",
    body: payload,
  });
}

export function listKnowledgeDocuments(
  options: KnowledgeRequestOptions,
): Promise<KnowledgeDocumentListResponse> {
  return apiFetch<KnowledgeDocumentListResponse>("/knowledge/documents", options);
}

export function getKnowledgeDocument(
  documentId: string,
  options: KnowledgeRequestOptions,
): Promise<KnowledgeDocumentDetailResponse> {
  return apiFetch<KnowledgeDocumentDetailResponse>(
    `/knowledge/documents/${encodeURIComponent(documentId)}`,
    options,
  );
}
