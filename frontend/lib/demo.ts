export const LOCAL_DEMO_PASSWORD = "DemoPassword123!";

export const localDemoAccounts = [
  {
    role: "Manager",
    email: "manager@example.test",
    password: LOCAL_DEMO_PASSWORD,
    recommendation: "Use Manager for the main demo.",
  },
  {
    role: "Admin",
    email: "admin@example.test",
    password: LOCAL_DEMO_PASSWORD,
    recommendation: "Use Admin for operational checks.",
  },
  {
    role: "Sales",
    email: "sales@example.test",
    password: LOCAL_DEMO_PASSWORD,
    recommendation: "Use Sales to inspect workflow access.",
  },
  {
    role: "Viewer",
    email: "viewer@example.test",
    password: LOCAL_DEMO_PASSWORD,
    recommendation: "Use Viewer for read-only/RBAC checks.",
  },
] as const;

export const demoWorkflows = [
  {
    title: "Full demo",
    shortTitle: "Run from CREATED",
    status: "CREATED",
    workflowId: "dc5e7963-c2a4-5ad6-8f70-0741431597f0",
    purpose: "Start here for the full end-to-end workflow run.",
    nextStep: "Run workflow, then review the WAITING_APPROVAL boundary.",
  },
  {
    title: "Fast demo",
    shortTitle: "Approve and resume",
    status: "WAITING_APPROVAL",
    workflowId: "b0111d45-aff5-5b86-9ffd-9417704c9bab",
    purpose: "Use this when time is short and approval is the focus.",
    nextStep: "Review details, approve, then resume.",
  },
  {
    title: "Resume-ready workflow",
    shortTitle: "Resume-only demo",
    status: "APPROVED",
    workflowId: "e1771f90-a85e-5684-98d1-7dd0458a4e89",
    purpose: "Use this to show post-approval continuation only.",
    nextStep: "Resume workflow and verify COMPLETED.",
  },
  {
    title: "Completed workflow",
    shortTitle: "Completed history",
    status: "COMPLETED",
    workflowId: "6b99fd38-1ecf-5213-8d69-43abcca20856",
    purpose: "Use this as read-only proof of the final timeline.",
    nextStep: "Review state, approval history, evidence, and events.",
  },
] as const;

export const workflowLifecycle = [
  "Request",
  "Run",
  "WAITING_APPROVAL",
  "Approve",
  "Resume",
  "COMPLETED",
] as const;
