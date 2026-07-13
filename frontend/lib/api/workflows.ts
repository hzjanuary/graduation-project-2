import { apiFetch, type ApiFetchOptions } from "@/lib/api/client";
import type {
  WorkflowCreateRequest,
  WorkflowEventListResponse,
  WorkflowListResponse,
  WorkflowResponse,
  WorkflowRunResponse,
  WorkflowStatus,
} from "@/lib/api/types";

type WorkflowRequestOptions = Pick<ApiFetchOptions, "baseUrl" | "fetcher"> & {
  token: string;
};

export interface WorkflowListParams {
  limit?: number;
  offset?: number;
  status?: WorkflowStatus | null;
}

export function listWorkflows(
  options: WorkflowRequestOptions,
  params: WorkflowListParams = {},
): Promise<WorkflowListResponse> {
  return apiFetch<WorkflowListResponse>("/workflows", {
    ...options,
    query: {
      limit: params.limit ?? 100,
      offset: params.offset ?? 0,
      status: params.status ?? undefined,
    },
  });
}

export function getWorkflow(
  workflowId: string,
  options: WorkflowRequestOptions,
): Promise<WorkflowResponse> {
  return apiFetch<WorkflowResponse>(`/workflows/${workflowId}`, options);
}

export function createWorkflow(
  payload: WorkflowCreateRequest,
  options: WorkflowRequestOptions,
): Promise<WorkflowResponse> {
  return apiFetch<WorkflowResponse>("/workflows", {
    ...options,
    method: "POST",
    body: payload,
  });
}

export function runWorkflow(
  workflowId: string,
  options: WorkflowRequestOptions,
): Promise<WorkflowRunResponse> {
  return apiFetch<WorkflowRunResponse>(`/workflows/${workflowId}/run`, {
    ...options,
    method: "POST",
  });
}

export function listWorkflowEvents(
  workflowId: string,
  options: WorkflowRequestOptions,
  params: Pick<WorkflowListParams, "limit" | "offset"> = {},
): Promise<WorkflowEventListResponse> {
  return apiFetch<WorkflowEventListResponse>(`/workflows/${workflowId}/events`, {
    ...options,
    query: {
      limit: params.limit ?? 25,
      offset: params.offset ?? 0,
    },
  });
}
