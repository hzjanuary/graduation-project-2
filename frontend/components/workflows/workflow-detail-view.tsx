"use client";

import { useEffect, useState } from "react";

import { WorkflowDetail } from "@/components/workflows/workflow-detail";
import { WorkflowEventTimeline } from "@/components/workflows/workflow-event-timeline";
import { workflowErrorMessage } from "@/components/workflows/workflow-list-view";
import { WorkflowRunPanel } from "@/components/workflows/workflow-run-panel";
import { getWorkflow, listWorkflowEvents } from "@/lib/api/workflows";
import { getAccessToken } from "@/lib/auth/session";
import type { WorkflowEvent, WorkflowState } from "@/lib/api/types";

type DetailState =
  | { status: "loading" }
  | { status: "login-required" }
  | { status: "error"; message: string }
  | { status: "ready"; workflow: WorkflowState; events: WorkflowEvent[] };

interface WorkflowDetailViewProps {
  workflowId: string;
}

export function WorkflowDetailView({ workflowId }: WorkflowDetailViewProps) {
  const [state, setState] = useState<DetailState>({ status: "loading" });

  useEffect(() => {
    let isMounted = true;
    const token = getAccessToken();

    if (!token) {
      setState({ status: "login-required" });
      return;
    }

    loadWorkflowDetail(workflowId, token)
      .then(({ workflow, events }) => {
        if (isMounted) {
          setState({
            status: "ready",
            workflow,
            events,
          });
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
  }, [workflowId]);

  if (state.status === "loading") {
    return <DetailStatePanel title="Loading workflow detail" />;
  }

  if (state.status === "login-required") {
    return (
      <DetailStatePanel
        title="Login required"
        description="Sign in before loading this workflow from the backend."
      />
    );
  }

  if (state.status === "error") {
    return (
      <DetailStatePanel
        title="Unable to load workflow"
        description={state.message}
      />
    );
  }

  async function refreshWorkflowDetail() {
    const token = getAccessToken();
    if (!token) {
      setState({ status: "login-required" });
      return;
    }

    const { workflow, events } = await loadWorkflowDetail(workflowId, token);
    setState({ status: "ready", workflow, events });
  }

  return (
    <div className="grid gap-6">
      <WorkflowRunPanel
        workflowId={state.workflow.workflow_id}
        onRunCompleted={refreshWorkflowDetail}
      />
      <WorkflowDetail workflow={state.workflow} />
      <WorkflowEventTimeline
        workflowId={state.workflow.workflow_id}
        persistedEvents={state.events}
      />
    </div>
  );
}

async function loadWorkflowDetail(workflowId: string, token: string) {
  const [workflowResponse, eventResponse] = await Promise.all([
    getWorkflow(workflowId, { token }),
    listWorkflowEvents(workflowId, { token }, { limit: 25, offset: 0 }),
  ]);

  return {
    workflow: workflowResponse.workflow,
    events: eventResponse.events,
  };
}

function DetailStatePanel({
  title,
  description = "This view will update after the backend response is available.",
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        {description}
      </p>
    </div>
  );
}
