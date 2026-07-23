"use client";

import { useState } from "react";

import { ApiClientError } from "@/lib/api/client";
import { searchKnowledge } from "@/lib/api/knowledge";
import type {
  KnowledgeRetrievalResult,
  KnowledgeSearchResponse,
} from "@/lib/api/types";

const DEFAULT_TOP_K = 3;

type SearchState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; response: KnowledgeSearchResponse }
  | { status: "error"; message: string };

interface KnowledgeSearchPanelProps {
  token: string;
}

export function KnowledgeSearchPanel({ token }: KnowledgeSearchPanelProps) {
  const [query, setQuery] = useState("procurement policy approval evidence");
  const [topK, setTopK] = useState(DEFAULT_TOP_K);
  const [state, setState] = useState<SearchState>({ status: "idle" });

  async function submitSearch() {
    if (!query.trim()) {
      setState({ status: "error", message: "Enter a knowledge search query." });
      return;
    }

    setState({ status: "loading" });
    try {
      const response = await searchKnowledge(
        { query: query.trim(), top_k: topK },
        { token },
      );
      setState({ status: "success", response });
    } catch (error) {
      setState({ status: "error", message: knowledgeErrorMessage(error) });
    }
  }

  return (
    <section className="ops-panel p-5">
      <div>
        <p className="ops-kicker">
          Knowledge search
        </p>
        <h2 className="mt-1 text-lg font-semibold">Search demo knowledge</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          Search the ingested procurement knowledge base. Results return bounded
          citation excerpts; no raw embeddings or vector payloads are shown.
        </p>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_8rem_auto]">
        <label className="grid gap-2 text-sm font-medium">
          Query
          <input
            className="ops-input h-10 font-normal"
            maxLength={2000}
            onChange={(event) => setQuery(event.target.value)}
            value={query}
          />
        </label>
        <label className="grid gap-2 text-sm font-medium">
          Top K
          <input
            className="ops-input h-10 font-normal"
            max={20}
            min={1}
            onChange={(event) => setTopK(Number(event.target.value))}
            type="number"
            value={topK}
          />
        </label>
        <button
          className="ops-button-primary mt-auto"
          disabled={state.status === "loading"}
          onClick={() => void submitSearch()}
          type="button"
        >
          {state.status === "loading" ? "Searching..." : "Search"}
        </button>
      </div>

      {state.status === "error" ? (
        <div className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {state.message}
        </div>
      ) : null}

      {state.status === "success" ? (
        state.response.results.length === 0 ? (
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            No knowledge results matched that query. Ingest the demo knowledge
            base before expecting populated search results.
          </p>
        ) : (
          <ol className="mt-5 grid gap-3">
            {state.response.results.map((result) => (
              <SearchResultItem key={result.chunk_id} result={result} />
            ))}
          </ol>
        )
      ) : null}
    </section>
  );
}

function SearchResultItem({ result }: { result: KnowledgeRetrievalResult }) {
  return (
    <li className="rounded-md border border-border/70 bg-background/55 p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="break-words text-sm font-semibold">
            {result.citation.document_title}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {result.source_type} / {result.citation.citation_label}
          </p>
        </div>
        <span className="ops-chip">
          Score {Math.round(result.score * 100)}%
        </span>
      </div>
      <p className="mt-3 max-h-28 overflow-hidden whitespace-pre-wrap break-words text-sm leading-6 text-muted-foreground">
        {result.citation.excerpt}
      </p>
      <p className="mt-3 break-all text-xs text-muted-foreground">
        Document: {result.document_id}
      </p>
    </li>
  );
}

function knowledgeErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Sign in before searching the knowledge base.";
    }
    if (error.status === 403) {
      return "Your account cannot search the knowledge base.";
    }
    if (error.status === 422) {
      return "Check the search query and filters, then try again.";
    }
    if (error.status === 503) {
      return "Knowledge retrieval is unavailable. Confirm Qdrant is running and demo knowledge has been ingested.";
    }
    return error.message;
  }
  return "Knowledge search failed. Try again later.";
}
