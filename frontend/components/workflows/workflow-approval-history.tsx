import type { ApprovalHistoryResponse, ApprovalRecord } from "@/lib/api/types";

interface WorkflowApprovalHistoryProps {
  history: ApprovalHistoryResponse;
}

export function WorkflowApprovalHistory({
  history,
}: WorkflowApprovalHistoryProps) {
  return (
    <section className="rounded-lg border bg-card p-5 text-card-foreground shadow-sm">
      <div>
        <p className="text-sm font-medium text-muted-foreground">
          Human approval
        </p>
        <h2 className="mt-1 text-lg font-semibold">Approval history</h2>
      </div>

      {history.approvals.length === 0 ? (
        <p className="mt-4 text-sm leading-6 text-muted-foreground">
          No approval decisions have been recorded for this workflow yet.
        </p>
      ) : (
        <ol className="mt-5 grid gap-3">
          {history.approvals.map((approval) => (
            <ApprovalHistoryItem
              approval={approval}
              key={approval.decision_id}
            />
          ))}
        </ol>
      )}
    </section>
  );
}

function ApprovalHistoryItem({ approval }: { approval: ApprovalRecord }) {
  return (
    <li className="rounded-md border bg-background p-3">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium">
            {approvalDecisionLabel(approval.decision)}
          </p>
          <p className="mt-1 break-all text-xs text-muted-foreground">
            {approval.actor_email ?? approval.actor_id}
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          {formatDate(approval.decided_at)}
        </p>
      </div>
      {approval.comment ? (
        <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-muted-foreground">
          {approval.comment}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
        <span>Previous: {approval.previous_status}</span>
        <span>Next: {approval.next_status ?? "Not changed"}</span>
      </div>
    </li>
  );
}

function approvalDecisionLabel(decision: ApprovalRecord["decision"]): string {
  if (decision === "approve") {
    return "Approved";
  }
  if (decision === "reject") {
    return "Rejected";
  }
  return "Changes requested";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
