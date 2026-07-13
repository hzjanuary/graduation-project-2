"use client";

import { useState } from "react";

import { ApiClientError } from "@/lib/api/client";
import { runWorkflow } from "@/lib/api/workflows";
import { getAccessToken } from "@/lib/auth/session";
import type { WorkflowRunResponse } from "@/lib/api/types";

type RunState =
  | { status: "idle" }
  | { status: "running" }
  | { status: "success"; response: WorkflowRunResponse }
  | { status: "error"; message: string };

interface WorkflowRunPanelProps {
  workflowId: string;
  onRunCompleted?: () => Promise<void> | void;
}

export function WorkflowRunPanel({
  workflowId,
  onRunCompleted,
}: WorkflowRunPanelProps) {
  const [runState, setRunState] = useState<RunState>({ status: "idle" });

  async function handleRun() {
    const token = getAccessToken();
    if (!token) {
      setRunState({
        status: "error",
        message: "Sign in before running this workflow.",
      });
      return;
    }

    setRunState({ status: "running" });
    try {
      const response = await runWorkflow(workflowId, { token });
      setRunState({ status: "success", response });
      await onRunCompleted?.();
    } catch (error) {
      setRunState({ status: "error", message: runErrorMessage(error) });
    }
  }

  const isRunning = runState.status === "running";

  return (
    <section className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">
            Runtime action
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">
            Run deterministic workflow
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Starts the existing backend runtime and stops at waiting approval.
            Live WebSocket timeline behavior is deferred to TASK 009.6.
          </p>
        </div>
        <button
          className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isRunning}
          onClick={handleRun}
          type="button"
        >
          {isRunning ? "Running..." : "Run workflow"}
        </button>
      </div>

      {runState.status === "success" ? (
        <RuntimeResult response={runState.response} />
      ) : null}

      {runState.status === "error" ? (
        <div className="mt-5 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {runState.message}
        </div>
      ) : null}
    </section>
  );
}

function RuntimeResult({ response }: { response: WorkflowRunResponse }) {
  return (
    <div className="mt-5 grid gap-4 rounded-md border bg-muted/50 p-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <ResultItem label="Status" value={response.status} />
        <ResultItem
          label="Waiting approval"
          value={response.waiting_for_approval ? "Yes" : "No"}
        />
        <ResultItem label="Completed" value={response.completed ? "Yes" : "No"} />
      </div>
      <div>
        <h3 className="text-sm font-semibold">Runtime result</h3>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {response.message ??
            "Runtime returned successfully. Check persisted events below for progress evidence."}
        </p>
      </div>
      <div>
        <h3 className="text-sm font-semibold">Completed stages</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          {response.completed_stages.length > 0
            ? response.completed_stages.join(", ")
            : "No completed stages reported."}
        </p>
      </div>
    </div>
  );
}

function ResultItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}

function runErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Your session is not authorized. Sign in again.";
    }
    if (error.status === 403) {
      return "Your account cannot run workflows.";
    }
    if (error.status === 409) {
      return error.message || "This workflow cannot be run from its current state.";
    }
    return error.message;
  }
  return "The workflow runtime is unavailable. Try again later.";
}
