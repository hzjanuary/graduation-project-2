"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { ApiClientError } from "@/lib/api/client";
import { createWorkflow } from "@/lib/api/workflows";
import { getAccessToken } from "@/lib/auth/session";
import type { WorkflowCreateRequest, WorkflowState } from "@/lib/api/types";

const DEFAULT_DOMAIN = "it_equipment";
const DEFAULT_ITEMS_JSON = `[
  {
    "name": "Standard business laptop",
    "quantity": 50
  }
]`;
const DEFAULT_METADATA_JSON = `{
  "tags": {
    "source": "frontend-demo"
  },
  "attributes": {}
}`;

type SubmitState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "success"; workflow: WorkflowState }
  | { status: "error"; message: string };

export interface WorkflowCreateFormValues {
  domain: string;
  customerName: string;
  rawText: string;
  itemsJson: string;
  metadataJson: string;
}

export class WorkflowCreateFormValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WorkflowCreateFormValidationError";
  }
}

export function WorkflowCreateForm() {
  const [submitState, setSubmitState] = useState<SubmitState>({ status: "idle" });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getAccessToken();

    if (!token) {
      setSubmitState({
        status: "error",
        message: "Sign in before creating a workflow.",
      });
      return;
    }

    let payload: WorkflowCreateRequest;
    try {
      payload = buildWorkflowCreateRequest(valuesFromForm(event.currentTarget));
    } catch (error) {
      setSubmitState({
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "The workflow request is invalid.",
      });
      return;
    }

    setSubmitState({ status: "submitting" });
    try {
      const response = await createWorkflow(payload, { token });
      setSubmitState({ status: "success", workflow: response.workflow });
    } catch (error) {
      setSubmitState({ status: "error", message: createErrorMessage(error) });
    }
  }

  const isSubmitting = submitState.status === "submitting";

  return (
    <section className="ops-panel p-6">
      <div className="flex flex-col gap-2">
        <p className="ops-kicker">
          Procurement quotation
        </p>
        <h2 className="text-2xl font-semibold tracking-tight">
          Create workflow
        </h2>
        <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
          Submit manual request text to the existing workflow API. The backend
          creates the workflow; runtime execution remains a separate action on
          the detail page.
        </p>
      </div>

      <form className="mt-6 grid gap-5" onSubmit={handleSubmit}>
        <label className="grid gap-2 text-sm font-medium">
          Domain
          <input
            className="ops-input px-3 py-2"
            name="domain"
            defaultValue={DEFAULT_DOMAIN}
            placeholder="it_equipment"
          />
        </label>

        <label className="grid gap-2 text-sm font-medium">
          Customer name
          <input
            className="ops-input px-3 py-2"
            name="customerName"
            placeholder="Acme Manufacturing Group"
          />
        </label>

        <label className="grid gap-2 text-sm font-medium">
          Request text
          <textarea
            className="ops-input min-h-32 px-3 py-2 leading-6"
            name="rawText"
            placeholder="We would like to purchase 50 standard business laptops..."
            required
          />
        </label>

        <label className="grid gap-2 text-sm font-medium">
          Items JSON
          <textarea
            className="ops-input min-h-36 px-3 py-2 font-mono text-xs leading-5"
            name="itemsJson"
            defaultValue={DEFAULT_ITEMS_JSON}
          />
        </label>

        <label className="grid gap-2 text-sm font-medium">
          Metadata JSON
          <textarea
            className="ops-input min-h-32 px-3 py-2 font-mono text-xs leading-5"
            name="metadataJson"
            defaultValue={DEFAULT_METADATA_JSON}
          />
        </label>

        <div className="flex flex-col gap-3 border-t border-border/70 pt-5 sm:flex-row sm:items-center">
          <button
            className="ops-button-primary"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Creating..." : "Create workflow"}
          </button>
          <p className="text-sm text-muted-foreground">
            Uses POST /api/v1/workflows; no runtime or stream is started here.
          </p>
        </div>
      </form>

      {submitState.status === "success" ? (
        <div className="mt-5 rounded-md border border-emerald-400/30 bg-emerald-400/10 p-4 text-sm text-emerald-200">
          <p className="font-semibold">Workflow created.</p>
          <p className="mt-1 break-all">
            Status: {submitState.workflow.status} / ID:{" "}
            {submitState.workflow.workflow_id}
          </p>
          <Link
            className="mt-3 inline-flex text-sm font-medium underline underline-offset-4"
            href={`/workflows/${submitState.workflow.workflow_id}`}
          >
            Open workflow detail
          </Link>
        </div>
      ) : null}

      {submitState.status === "error" ? (
        <div className="mt-5 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {submitState.message}
        </div>
      ) : null}
    </section>
  );
}

export function buildWorkflowCreateRequest(
  values: WorkflowCreateFormValues,
): WorkflowCreateRequest {
  const rawText = values.rawText.trim();
  if (!rawText) {
    throw new WorkflowCreateFormValidationError("Request text is required.");
  }

  const items = parseJson(values.itemsJson, "Items JSON");
  if (!Array.isArray(items)) {
    throw new WorkflowCreateFormValidationError("Items JSON must be an array.");
  }

  const metadataInput = values.metadataJson.trim()
    ? parseJson(values.metadataJson, "Metadata JSON")
    : {};
  if (!isPlainObject(metadataInput)) {
    throw new WorkflowCreateFormValidationError(
      "Metadata JSON must be an object.",
    );
  }

  const customerName = values.customerName.trim();
  const request: Record<string, unknown> = {
    raw_text: rawText,
    source: "manual_text",
    items,
  };
  if (customerName) {
    request.customer = { name: customerName };
  }

  return {
    workflow_type: "procurement_quotation",
    domain: values.domain.trim() || null,
    request,
    metadata: {
      state_version: 1,
      ...metadataInput,
    },
  };
}

function valuesFromForm(form: HTMLFormElement): WorkflowCreateFormValues {
  const formData = new FormData(form);
  return {
    domain: formValue(formData, "domain"),
    customerName: formValue(formData, "customerName"),
    rawText: formValue(formData, "rawText"),
    itemsJson: formValue(formData, "itemsJson"),
    metadataJson: formValue(formData, "metadataJson"),
  };
}

function formValue(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value : "";
}

function parseJson(value: string, label: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    throw new WorkflowCreateFormValidationError(`${label} is not valid JSON.`);
  }
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function createErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Your session is not authorized. Sign in again.";
    }
    if (error.status === 403) {
      return "Your account cannot create workflows.";
    }
    return error.message;
  }
  return "The workflow could not be created. Try again later.";
}
