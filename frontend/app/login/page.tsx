"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { ApiClientError } from "@/lib/api/client";
import { login } from "@/lib/api/auth";
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
    <main className="min-h-screen bg-background">
      <section className="mx-auto grid min-h-screen w-full max-w-5xl gap-8 px-6 py-16 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)] lg:items-center">
        <div className="flex flex-col gap-3">
          <p className="text-sm font-medium text-muted-foreground">
            Enterprise Multi-Agent OS
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            Sign in
          </h1>
          <p className="text-sm leading-6 text-muted-foreground">
            Use the local-demo Manager account for the main evaluator flow.
            These credentials are for local-demo and board-demo use only, not
            production secrets.
          </p>
          <button
            className="mt-3 inline-flex h-10 w-fit items-center rounded-md border px-4 text-sm font-medium hover:bg-muted"
            onClick={fillManagerAccount}
            type="button"
          >
            Fill Manager
          </button>
        </div>

        <div className="grid gap-5">
          <form
            className="flex flex-col gap-4 rounded-lg border bg-card p-6 text-card-foreground shadow-sm"
            onSubmit={handleSubmit}
          >
            <label className="flex flex-col gap-2 text-sm font-medium">
              Email
              <input
                className="h-10 rounded-md border bg-background px-3 text-sm outline-none ring-offset-background transition focus-visible:ring-2 focus-visible:ring-ring"
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
                className="h-10 rounded-md border bg-background px-3 text-sm outline-none ring-offset-background transition focus-visible:ring-2 focus-visible:ring-ring"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            <button
              className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Signing in..." : "Sign in"}
            </button>
            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
            {isSignedIn ? (
              <p className="text-sm text-muted-foreground" role="status">
                Signed in.{" "}
                <Link
                  className="font-medium text-primary underline"
                  href="/dashboard"
                >
                  Open the dashboard.
                </Link>
              </p>
            ) : null}
          </form>

          <section className="rounded-lg border bg-card p-5 text-card-foreground shadow-sm">
            <h2 className="text-base font-semibold">Local demo accounts</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Use Manager for the main demo. These accounts come from the demo
              seed and must not be reused as production accounts.
            </p>
            <div className="mt-4 grid gap-3">
              {localDemoAccounts.map((account) => (
                <div className="rounded-md border bg-background p-3" key={account.email}>
                  <p className="text-sm font-semibold">{account.role}</p>
                  <p className="mt-1 break-all text-sm text-muted-foreground">
                    {account.email}
                  </p>
                  <p className="mt-1 break-all text-sm text-muted-foreground">
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

function userFacingError(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  return "Unable to sign in. Check your credentials and try again.";
}
