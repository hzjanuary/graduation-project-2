import type { WorkflowStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const terminalStatuses = new Set<WorkflowStatus>([
  "COMPLETED",
  "FAILED",
  "CANCELLED",
  "REJECTED",
]);

interface WorkflowStatusBadgeProps {
  status: WorkflowStatus;
}

export function WorkflowStatusBadge({ status }: WorkflowStatusBadgeProps) {
  const isTerminal = terminalStatuses.has(status);
  const isWaiting = status === "WAITING_APPROVAL";

  return (
    <span
      className={cn(
        "inline-flex w-fit items-center rounded-md border px-2 py-1 text-xs font-medium",
        isTerminal && "border-muted-foreground/30 bg-muted text-muted-foreground",
        isWaiting && "border-primary/30 bg-primary/10 text-primary",
        !isTerminal &&
          !isWaiting &&
          "border-emerald-500/30 bg-emerald-50 text-emerald-700",
      )}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}
