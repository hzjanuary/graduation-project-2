"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { login } from "@/lib/api/auth";
import { ApiClientError } from "@/lib/api/client";
import { setSessionTokens } from "@/lib/auth/session";
import { localDemoAccounts } from "@/lib/demo";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSignedIn, setIsSignedIn] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setIsSignedIn(false);

    try {
      const tokens = await login({ email, password });
      setSessionTokens(tokens);
      setIsSignedIn(true);
    } catch (caughtError) {
      setError(userFacingError(caughtError));
    } finally {
      setIsSubmitting(false);
    }
  }

  function fillManagerAccount() {
    const manager = localDemoAccounts.find((account) => account.role === "Manager");
    if (!manager) {
      return;
    }
    setEmail(manager.email);
    setPassword(manager.password);
  }

  return (
    <main className="ops-page">
      <section className="mx-auto grid min-h-screen w-full max-w-6xl gap-8 px-5 py-10 sm:px-6 lg:grid-cols-[minmax(0,1fr)_minmax(340px,460px)] lg:items-center lg:px-8">
        <div className="flex flex-col gap-6">
          <div>
            <p className="ops-kicker">Controlled access portal</p>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight text-foreground md:text-6xl">
              Sign in to the operations console.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground">
              This is not a chatbot. Use the local-demo Manager account to
              operate the deterministic workflow, inspect agent activity, and
              approve before resume.
            </p>
          </div>
          <LifecycleStrip />
          <button
            className="ops-button-secondary w-fit"
            onClick={fillManagerAccount}
            type="button"
          >
            Fill Manager
          </button>
        </div>

        <div className="grid gap-5">
          <form
            className="ops-panel-strong flex flex-col gap-4 p-6"
            onSubmit={handleSubmit}
          >
            <div>
              <p className="ops-kicker">Local demo session</p>
              <h2 className="mt-2 text-xl font-semibold">Login</h2>
            </div>
            <label className="flex flex-col gap-2 text-sm font-medium">
              Email
              <input
                className="ops-input h-11"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium">
              Password
              <input
                className="ops-input h-11"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            <button
              className="ops-button-primary"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Signing in..." : "Sign in"}
            </button>
            {error ? (
              <p
                className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
                role="alert"
              >
                {error}
              </p>
            ) : null}
            {isSignedIn ? (
              <p className="text-sm text-muted-foreground" role="status">
                Signed in.{" "}
                <Link className="font-medium text-primary underline" href="/dashboard">
                  Open the dashboard.
                </Link>
              </p>
            ) : null}
          </form>

          <section className="ops-panel p-5">
            <h2 className="text-base font-semibold">Local demo accounts</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Use Manager for the main demo. These accounts come from the demo
              seed and must not be reused as production accounts.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {localDemoAccounts.map((account) => (
                <div className="ops-panel-muted p-3" key={account.email}>
                  <p className="text-sm font-semibold">{account.role}</p>
                  <p className="mt-1 break-all text-sm text-muted-foreground">
                    {account.email}
                  </p>
                  <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
                    {account.password}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

function LifecycleStrip() {
  return (
    <div className="ops-panel grid gap-3 p-4 sm:grid-cols-4">
      {["Run", "WAITING_APPROVAL", "Approve", "Resume"].map((step) => (
        <div
          className="rounded-md border border-border/70 bg-background/50 px-3 py-2 text-center text-xs font-semibold text-muted-foreground"
          key={step}
        >
          {step}
        </div>
      ))}
    </div>
  );
}

function userFacingError(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  return "Unable to sign in. Check your credentials and try again.";
}
