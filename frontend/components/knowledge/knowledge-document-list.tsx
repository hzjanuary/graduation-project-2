"use client";

import { useEffect, useState } from "react";

import { ApiClientError } from "@/lib/api/client";
import { listKnowledgeDocuments } from "@/lib/api/knowledge";
import type {
  KnowledgeDocumentCatalogItem,
  KnowledgeDocumentListResponse,
} from "@/lib/api/types";

type DocumentListState =
  | { status: "loading" }
  | { status: "success"; response: KnowledgeDocumentListResponse }
  | { status: "error"; message: string };

interface KnowledgeDocumentListProps {
  token: string;
}

export function KnowledgeDocumentList({ token }: KnowledgeDocumentListProps) {
  const [state, setState] = useState<DocumentListState>({ status: "loading" });

  useEffect(() => {
    let isMounted = true;
    listKnowledgeDocuments({ token })
      .then((response) => {
        if (isMounted) {
          setState({ status: "success", response });
        }
      })
      .catch((error: unknown) => {
        if (isMounted) {
          setState({ status: "error", message: catalogErrorMessage(error) });
        }
      });

    return () => {
      isMounted = false;
    };
  }, [token]);

  return (
    <section className="rounded-lg border bg-card p-5 text-card-foreground shadow-sm">
      <div>
        <p className="text-sm font-medium text-muted-foreground">
          Knowledge catalog
        </p>
        <h2 className="mt-1 text-lg font-semibold">Demo documents</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          Bounded metadata for deterministic demo knowledge documents. Upload,
          edit, and admin document management are not part of this screen.
        </p>
      </div>

      {state.status === "loading" ? (
        <p className="mt-4 text-sm leading-6 text-muted-foreground">
          Loading knowledge document catalog.
        </p>
      ) : null}

      {state.status === "error" ? (
        <div className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {state.message}
        </div>
      ) : null}

      {state.status === "success" ? (
        state.response.documents.length === 0 ? (
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            No demo knowledge documents are available.
          </p>
        ) : (
          <ol className="mt-5 grid gap-3">
            {state.response.documents.map((document) => (
              <DocumentItem document={document} key={document.document_id} />
            ))}
          </ol>
        )
      ) : null}
    </section>
  );
}

function DocumentItem({ document }: { document: KnowledgeDocumentCatalogItem }) {
  return (
    <li className="rounded-md border bg-background p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="break-words text-sm font-semibold">{document.title}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {document.source_type} / {document.domain}
            {document.version ? ` / ${document.version}` : ""}
          </p>
        </div>
        {document.effective_date ? (
          <span className="inline-flex w-fit rounded-full border px-2.5 py-1 text-xs text-muted-foreground">
            Effective {document.effective_date}
          </span>
        ) : null}
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
        <span className="break-all">ID: {document.document_id}</span>
        {document.owner_team ? <span>Owner: {document.owner_team}</span> : null}
        {document.tags.map((tag) => (
          <span className="rounded-full border px-2 py-0.5" key={tag}>
            {tag}
          </span>
        ))}
      </div>
    </li>
  );
}

function catalogErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Sign in before loading the knowledge catalog.";
    }
    if (error.status === 403) {
      return "Your account cannot read the knowledge catalog.";
    }
    return error.message;
  }
  return "Knowledge catalog could not be loaded.";
}
