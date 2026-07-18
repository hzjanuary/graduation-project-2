import React, { act, type ReactElement } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import DashboardPage from "@/app/dashboard/page";
import DemoPage from "@/app/demo/page";
import HomePage from "@/app/page";
import LoginPage from "@/app/login/page";
import { ACCESS_TOKEN_STORAGE_KEY } from "@/lib/auth/session";

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) {
    act(() => {
      root?.unmount();
    });
  }
  root = null;
  container?.remove();
  container = null;
  window.localStorage.clear();
});

describe("demo-first frontend UX", () => {
  it("renders the demo command center with seeded workflow links", async () => {
    await render(<DemoPage />);

    expect(document.body.textContent).toContain("Evaluator start here");
    expect(document.body.textContent).toContain("Operation map");
    expect(document.body.textContent).toContain("WAITING_APPROVAL");
    expect(document.body.textContent).toContain("manager@example.test");
    expect(document.body.textContent).toContain(
      "dc5e7963-c2a4-5ad6-8f70-0741431597f0",
    );
    expect(document.body.textContent).toContain("RAG is off by default");
    expect(
      document.querySelector('a[href="/login"]')?.textContent,
    ).toContain("Go to Login");
  });

  it("renders the final home page without stale bootstrap copy", async () => {
    await render(<HomePage />);

    expect(document.body.textContent).toContain("Start Demo");
    expect(document.body.textContent).toContain("not a chatbot");
    expect(document.body.textContent).not.toContain("Frontend bootstrap");
  });

  it("shows local demo accounts and fills Manager credentials without submit", async () => {
    await render(<LoginPage />);

    expect(document.body.textContent).toContain("Local demo accounts");
    expect(document.body.textContent).toContain("Use Manager for the main demo");

    await clickButton("Fill Manager");

    const email = document.querySelector('input[type="email"]') as
      | HTMLInputElement
      | null;
    const password = document.querySelector('input[type="password"]') as
      | HTMLInputElement
      | null;

    expect(email?.value).toBe("manager@example.test");
    expect(password?.value).toBe("DemoPassword123!");
  });

  it("renders dashboard command cards for authenticated sessions", async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "access-token");

    await render(<DashboardPage />);

    expect(document.body.textContent).toContain("Start here");
    expect(document.body.textContent).toContain("Workflow lifecycle");
    expect(document.body.textContent).toContain("Primary demo workflows");
    expect(document.body.textContent).toContain("Quality and evidence");
    expect(document.body.textContent).toContain("final-quality-gate.sh");
  });
});

async function render(element: ReactElement) {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root?.render(element);
  });
  await flushEffects();
}

async function clickButton(label: string) {
  const button = Array.from(document.querySelectorAll("button")).find(
    (candidate) => candidate.textContent === label,
  );
  if (!button) {
    throw new Error(`Expected button ${label} to exist`);
  }
  await act(async () => {
    button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
  await flushEffects();
}

async function flushEffects() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}
