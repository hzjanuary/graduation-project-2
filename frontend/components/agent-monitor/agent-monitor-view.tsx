"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { WorkflowAgentActivityPanel } from "@/components/workflows/workflow-agent-activity-panel";
import { WorkflowEventTimeline } from "@/components/workflows/workflow-event-timeline";
import { WorkflowNextStepGuide } from "@/components/workflows/workflow-next-step-guide";
import { workflowErrorMessage } from "@/components/workflows/workflow-list-view";
import { demoWorkflows } from "@/lib/demo";
import {
  getWorkflow,
  getWorkflowApprovalHistory,
  listWorkflowEvents,
  listWorkflows,
} from "@/lib/api/workflows";
import { getAccessToken } from "@/lib/auth/session";
import type {
  ApprovalHistoryResponse,
  WorkflowEvent,
  WorkflowState,
} from "@/lib/api/types";

type MonitorState =
  | { status: "loading" }
  | { status: "login-required" }
  | { status: "error"; message: string }
  | { status: "recent"; workflows: WorkflowState[] }
  | {
      status: "workflow";
      workflow: WorkflowState;
      events: WorkflowEvent[];
      approvalHistory: ApprovalHistoryResponse;
    };

interface AgentMonitorViewProps {
  workflowId?: string;
}

export function AgentMonitorView({ workflowId }: AgentMonitorViewProps) {
  const [state, setState] = useState<MonitorState>({ status: "loading" });

  useEffect(() => {
    let isMounted = true;
    const token = getAccessToken();

    if (!token) {
      setState({ status: "login-required" });
      return;
    }

    const load = workflowId
      ? loadWorkflowMonitor(workflowId, token)
      : listWorkflows({ token }, { limit: 8, offset: 0 }).then((response) => ({
          status: "recent" as const,
          workflows: response.workflows,
        }));

    load
      .then((nextState) => {
        if (isMounted) {
          setState(nextState);
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
    return <MonitorStatePanel title="Loading agent monitor" />;
  }

  if (state.status === "login-required") {
    return (
      <MonitorStatePanel
        title="Login required"
        description="Sign in before observing workflow agent activity."
      />
    );
  }

  if (state.status === "error") {
    return (
      <MonitorStatePanel
        title="Unable to load agent monitor"
        description={state.message}
      />
    );
  }

  if (state.status === "recent") {
    return <RecentWorkflowMonitor workflows={state.workflows} />;
  }

  return (
    <WorkflowMonitor
      approvalHistory={state.approvalHistory}
      events={state.events}
      workflow={state.workflow}
    />
  );
}

async function loadWorkflowMonitor(workflowId: string, token: string) {
  const [workflowResponse, eventResponse, approvalHistory] = await Promise.all([
    getWorkflow(workflowId, { token }),
    listWorkflowEvents(workflowId, { token }, { limit: 25, offset: 0 }),
    getWorkflowApprovalHistory(workflowId, { token }),
  ]);

  return {
    status: "workflow" as const,
    workflow: workflowResponse.workflow,
    events: eventResponse.events,
    approvalHistory,
  };
}

function RecentWorkflowMonitor({ workflows }: { workflows: WorkflowState[] }) {
  return (
    <div className="grid gap-6">
      <ObserverModeIntro />
      <section className="ops-panel p-6">
        <h2 className="text-lg font-semibold">Seeded demo shortcuts</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Use these stable workflows when you want a predictable board-demo
          state, or observe recently created workflows below when an external
          channel creates new requests.
        </p>
        <div className="mt-5 grid gap-4 lg:grid-cols-4">
          {demoWorkflows.map((workflow) => (
            <MonitorShortcutCard
              href={`/agent-monitor?workflowId=${workflow.workflowId}`}
              key={workflow.workflowId}
              label={workflow.title}
              status={workflow.status}
              subtitle={workflow.shortTitle}
              text={workflow.nextStep}
              workflowId={workflow.workflowId}
            />
          ))}
        </div>
      </section>
      <section className="ops-panel p-6">
        <h2 className="text-lg font-semibold">Recent workflows</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          This list uses the existing workflow API and does not create or modify
          records.
        </p>
        {workflows.length === 0 ? (
          <p className="mt-5 text-sm leading-6 text-muted-foreground">
            No recent workflows are available yet.
          </p>
        ) : (
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {workflows.map((workflow) => (
              <RecentWorkflowCard workflow={workflow} key={workflow.workflow_id} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function WorkflowMonitor({
  workflow,
  events,
  approvalHistory,
}: {
  workflow: WorkflowState;
  events: WorkflowEvent[];
  approvalHistory: ApprovalHistoryResponse;
}) {
  return (
    <div className="grid gap-6">
      <ObserverModeIntro />
      <section className="ops-panel-strong p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="ops-kicker">
              Observed workflow
            </p>
            <h2 className="mt-2 break-words text-xl font-semibold tracking-tight">
              {workflow.workflow_id}
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Monitor this workflow without changing backend state. Use the
              full workflow detail route for run, approval, resume, evidence,
              and catalog panels.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              className="ops-button-primary"
              href={`/workflows/${workflow.workflow_id}`}
            >
              Open full detail
            </Link>
            <Link
              className="ops-button-secondary"
              href={`/workflows/${workflow.workflow_id}`}
            >
              Approve / resume
            </Link>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MonitorFact label="Status" value={workflow.status} />
          <MonitorFact
            label="Domain"
            value={workflow.domain ?? "Not specified"}
          />
          <MonitorFact label="Type" value={workflow.workflow_type} />
          <MonitorFact
            label="Current step"
            value={workflow.current_step ?? "Not started"}
          />
        </div>
      </section>
      <WorkflowNextStepGuide status={workflow.status} />
      <WorkflowAgentActivityPanel
        approvalHistory={approvalHistory}
        events={events}
        workflow={workflow}
      />
      <WorkflowEventTimeline
        workflowId={workflow.workflow_id}
        persistedEvents={events}
      />
    </div>
  );
}

function ObserverModeIntro() {
  return (
    <section className="ops-panel-strong p-6">
      <p className="ops-kicker">
        Live demo observer mode
      </p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight">
        Watch workflow agents without reading the full runbook first.
      </h2>
      <div className="mt-4 grid gap-3 text-sm leading-6 text-muted-foreground lg:grid-cols-2">
        <p>
          External requests can create workflows, including channels such as a
          Telegram integration when configured outside this frontend. This page
          lets evaluators select a recent workflow or a seeded demo workflow and
          observe execution.
        </p>
        <p>
          Agents are deterministic workflow stages in no-key mode. The UI shows
          bounded operational evidence, not chain-of-thought, and human approval
          is still required before resume.
        </p>
      </div>
    </section>
  );
}

function MonitorShortcutCard({
  href,
  label,
  status,
  subtitle,
  text,
  workflowId,
}: {
  href: string;
  label: string;
  status: string;
  subtitle: string;
  text: string;
  workflowId: string;
}) {
  return (
    <Link
      className="ops-card-link p-5"
      href={href}
    >
      <p className="ops-kicker">{label}</p>
      <h3 className="mt-2 text-base font-semibold">{subtitle}</h3>
      <p className="mt-2 inline-flex rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">{status}</p>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{text}</p>
      <p className="mt-3 break-words text-xs leading-5 text-muted-foreground">
        {workflowId}
      </p>
    </Link>
  );
}

function RecentWorkflowCard({ workflow }: { workflow: WorkflowState }) {
  return (
    <Link
      className="ops-card-link p-5"
      href={`/agent-monitor?workflowId=${workflow.workflow_id}`}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="break-words text-base font-semibold">
            {workflow.workflow_id}
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {workflow.workflow_type}
          </p>
        </div>
        <span className="ops-chip">
          {workflow.status}
        </span>
      </div>
      <div className="mt-4 grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
        <span>Domain: {workflow.domain ?? "Not specified"}</span>
        <span>Step: {workflow.current_step ?? "Not started"}</span>
      </div>
    </Link>
  );
}

function MonitorFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="ops-panel-muted p-3">
      <p className="ops-kicker">
        {label}
      </p>
      <p className="mt-1 break-words text-sm font-semibold">{value}</p>
    </div>
  );
}

function MonitorStatePanel({
  title,
  description = "This view updates after the backend response is available.",
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
