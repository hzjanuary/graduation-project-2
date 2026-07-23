import type { WorkflowStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const terminalStatuses = new Set<WorkflowStatus>([
  "COMPLETED",
  "FAILED",
  "CANCELLED",
  "REJECTED",
]);
const runningStatuses: WorkflowStatus[] = [
  "PLANNING",
  "RETRIEVING",
  "CALCULATING",
  "CHECKING_COMPLIANCE",
  "VALIDATING",
  "GENERATING_EMAIL",
];

interface WorkflowStatusBadgeProps {
  status: WorkflowStatus;
}

export function WorkflowStatusBadge({ status }: WorkflowStatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
        status === "CREATED" && "ops-status-created",
        runningStatuses.includes(status) && "ops-status-running",
        status === "WAITING_APPROVAL" && "ops-status-waiting",
        status === "APPROVED" && "ops-status-approved",
        status === "COMPLETED" && "ops-status-completed",
        terminalStatuses.has(status) &&
          status !== "COMPLETED" &&
          "ops-status-danger",
      )}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}
