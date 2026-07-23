"use client";

import { useEffect, useState } from "react";

import { DemoWorkflowCards } from "@/components/demo/demo-workflow-cards";
import { WorkflowTable } from "@/components/workflows/workflow-table";
import { ApiClientError } from "@/lib/api/client";
import { listWorkflows } from "@/lib/api/workflows";
import { getAccessToken } from "@/lib/auth/session";
import type { WorkflowState } from "@/lib/api/types";

type LoadState =
  | { status: "loading" }
  | { status: "login-required" }
  | { status: "error"; message: string }
  | { status: "ready"; workflows: WorkflowState[] };

export function WorkflowListView() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let isMounted = true;
    const token = getAccessToken();

    if (!token) {
      setState({ status: "login-required" });
      return;
    }

    listWorkflows({ token }, { limit: 100, offset: 0 })
      .then((response) => {
        if (isMounted) {
          setState({ status: "ready", workflows: response.workflows });
        }
      })
      .catch((error: unknown) => {
        if (isMounted) {
          setState({ status: "error", message: workflowErrorMessage(error) });
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  if (state.status === "loading") {
    return <WorkflowStatePanel title="Loading workflows" />;
  }

  if (state.status === "login-required") {
    return (
      <WorkflowStatePanel
        title="Login required"
        description="Sign in before loading workflow records from the backend."
      />
    );
  }

  if (state.status === "error") {
    return (
      <WorkflowStatePanel
        title="Unable to load workflows"
        description={state.message}
      />
    );
  }

  return (
    <div className="grid gap-6">
      <section className="ops-panel-strong p-6">
        <p className="ops-kicker">Operator queue</p>
        <h2 className="text-lg font-semibold">Demo workflow chooser</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Use the CREATED workflow for the full run, WAITING_APPROVAL for a
          fast approve/resume demo, APPROVED for resume-only, or COMPLETED for
          read-only history proof.
        </p>
        <div className="mt-5">
          <DemoWorkflowCards compact />
        </div>
      </section>
      <WorkflowTable workflows={state.workflows} />
    </div>
  );
}

export function workflowErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Your session is not authorized. Sign in again.";
    }
    if (error.status === 403) {
      return "Your account does not have workflow read access.";
    }
    if (error.status === 404) {
      return "The requested workflow was not found.";
    }
    return error.message;
  }
  return "The workflow service is unavailable. Try again later.";
}

function WorkflowStatePanel({
  title,
  description = "This view will update after the backend response is available.",
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="ops-panel p-6">
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        {description}
      </p>
    </div>
  );
}
