"use client";

import type {
  KnowledgeCitation,
  WorkflowEvent,
  WorkflowEvidenceCitation,
  WorkflowState,
} from "@/lib/api/types";

const MAX_EXCERPT_DISPLAY_CHARS = 520;
const SENSITIVE_FIELD_MARKERS = [
  "embedding",
  "vector",
  "raw_prompt",
  "provider_payload",
  "chain_of_thought",
  "api_key",
  "secret",
  "token",
];

interface WorkflowEvidencePanelProps {
  workflow: WorkflowState;
  events?: WorkflowEvent[];
}

export function WorkflowEvidencePanel({
  workflow,
  events = [],
}: WorkflowEvidencePanelProps) {
  const citations = extractWorkflowEvidence(workflow, events);
  const groups = groupByStage(citations);

  return (
    <section className="rounded-lg border bg-card p-5 text-card-foreground shadow-sm">
      <div>
        <p className="text-sm font-medium text-muted-foreground">
          Retrieved evidence
        </p>
        <h2 className="mt-1 text-lg font-semibold">Evidence and citations</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          Citations attached by the RAG-enabled runtime support human review;
          they are not legal advice or a final compliance decision.
        </p>
      </div>

      {citations.length === 0 ? (
        <p className="mt-4 text-sm leading-6 text-muted-foreground">
          No retrieved evidence has been attached yet.
        </p>
      ) : (
        <div className="mt-5 grid gap-5">
          {groups.map(([stage, stageCitations]) => (
            <div className="grid gap-3" key={stage}>
              <h3 className="text-sm font-semibold">{stageLabel(stage)}</h3>
              <div className="grid gap-3 lg:grid-cols-2">
                {stageCitations.map((citation) => (
                  <CitationCard citation={citation} key={citationKey(citation)} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function extractWorkflowEvidence(
  workflow: WorkflowState,
  events: WorkflowEvent[] = [],
): WorkflowEvidenceCitation[] {
  const citations: WorkflowEvidenceCitation[] = [];

  collectRuntimeContextEvidence(workflow.runtime_context, citations);
  collectOutputsEvidence(workflow.outputs, citations);
  collectStageOutputsEvidence(workflow.stage_outputs, citations);
  collectEventEvidence(events, citations);

  const seen = new Set<string>();
  return citations.filter((citation) => {
    const key = citationKey(citation);
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function CitationCard({ citation }: { citation: WorkflowEvidenceCitation }) {
  const location = citationLocation(citation);

  return (
    <article className="rounded-md border bg-background p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="break-words text-sm font-semibold">
            {citation.document_title}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {citation.source_type} / {citation.citation_label}
          </p>
        </div>
        <span className="inline-flex w-fit rounded-full border px-2.5 py-1 text-xs text-muted-foreground">
          Score {formatScore(citation.relevance_score)}
        </span>
      </div>
      {location ? (
        <p className="mt-3 text-xs text-muted-foreground">{location}</p>
      ) : null}
      <p className="mt-3 max-h-32 overflow-hidden whitespace-pre-wrap break-words text-sm leading-6 text-muted-foreground">
        {boundedDisplay(citation.excerpt)}
      </p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
        <span className="break-all">Document: {citation.document_id}</span>
        {citation.reason ? <span>Reason: {citation.reason}</span> : null}
      </div>
    </article>
  );
}

function collectRuntimeContextEvidence(
  runtimeContext: Record<string, unknown> | undefined,
  target: WorkflowEvidenceCitation[],
) {
  const rag = asRecord(runtimeContext?.rag);
  const stages = asRecord(rag?.stages);

  if (stages) {
    for (const [stage, payload] of Object.entries(stages)) {
      collectCitationArray(asRecord(payload)?.citations, target, stage);
    }
  }

  collectCitationArray(rag?.citations, target, null);
}

function collectOutputsEvidence(
  outputs: Record<string, unknown> | undefined,
  target: WorkflowEvidenceCitation[],
) {
  const evidence = outputs?.evidence;
  collectEvidenceValue(evidence, target, null);
}

function collectStageOutputsEvidence(
  stageOutputs: WorkflowState["stage_outputs"],
  target: WorkflowEvidenceCitation[],
) {
  for (const [stage, payload] of Object.entries(stageOutputs ?? {})) {
    collectEvidenceValue(asRecord(payload)?.evidence, target, stage);
  }
}

function collectEventEvidence(
  events: WorkflowEvent[],
  target: WorkflowEvidenceCitation[],
) {
  for (const event of events) {
    if (!event.event_type.startsWith("knowledge.grounding.")) {
      continue;
    }
    const stage = typeof event.payload.stage === "string" ? event.payload.stage : null;
    collectEvidenceValue(event.payload.citations, target, stage);
    collectEvidenceValue(event.payload.evidence, target, stage);
  }
}

function collectEvidenceValue(
  value: unknown,
  target: WorkflowEvidenceCitation[],
  fallbackStage: string | null,
) {
  if (Array.isArray(value)) {
    collectCitationArray(value, target, fallbackStage);
    return;
  }

  const evidenceRecord = asRecord(value);
  if (!evidenceRecord) {
    return;
  }

  for (const [stage, maybeCitations] of Object.entries(evidenceRecord)) {
    collectCitationArray(maybeCitations, target, stage);
  }
}

function collectCitationArray(
  value: unknown,
  target: WorkflowEvidenceCitation[],
  fallbackStage: string | null,
) {
  if (!Array.isArray(value)) {
    return;
  }

  for (const item of value) {
    const citation = toEvidenceCitation(item, fallbackStage);
    if (citation) {
      target.push(citation);
    }
  }
}

function toEvidenceCitation(
  value: unknown,
  fallbackStage: string | null,
): WorkflowEvidenceCitation | null {
  const candidate = asRecord(value);
  if (!candidate || containsSensitiveField(candidate)) {
    return null;
  }

  const citation_id = asString(candidate.citation_id);
  const document_id = asString(candidate.document_id);
  const document_title = asString(candidate.document_title);
  const source_type = asString(candidate.source_type) as KnowledgeCitation["source_type"];
  const citation_label = asString(candidate.citation_label);
  const excerpt = asString(candidate.excerpt);
  const relevance_score = asNumber(candidate.relevance_score);

  if (
    !citation_id ||
    !document_id ||
    !document_title ||
    !source_type ||
    !citation_label ||
    !excerpt ||
    relevance_score === null
  ) {
    return null;
  }

  return {
    citation_id,
    document_id,
    document_title,
    source_type,
    section: asString(candidate.section),
    page: asNumber(candidate.page),
    excerpt: excerpt.slice(0, 1200),
    relevance_score,
    citation_label,
    stage: asString(candidate.stage) ?? fallbackStage,
    reason: asString(candidate.reason),
  };
}

function containsSensitiveField(value: Record<string, unknown>): boolean {
  return Object.keys(value).some((key) => {
    const normalized = key.toLowerCase();
    return SENSITIVE_FIELD_MARKERS.some((marker) => normalized.includes(marker));
  });
}

function groupByStage(
  citations: WorkflowEvidenceCitation[],
): [string, WorkflowEvidenceCitation[]][] {
  const groups = new Map<string, WorkflowEvidenceCitation[]>();
  for (const citation of citations) {
    const stage = citation.stage || "unassigned";
    groups.set(stage, [...(groups.get(stage) ?? []), citation]);
  }
  return Array.from(groups.entries());
}

function citationKey(citation: WorkflowEvidenceCitation): string {
  return [
    citation.stage ?? "unassigned",
    citation.citation_id,
    citation.document_id,
    citation.excerpt,
  ].join("|");
}

function citationLocation(citation: WorkflowEvidenceCitation): string | null {
  const parts: string[] = [];
  if (citation.section) {
    parts.push(`Section: ${citation.section}`);
  }
  if (citation.page) {
    parts.push(`Page: ${citation.page}`);
  }
  return parts.length > 0 ? parts.join(" / ") : null;
}

function stageLabel(stage: string): string {
  if (stage === "validation") {
    return "Validation and finance";
  }
  if (stage === "approval") {
    return "Approval package";
  }
  if (stage === "compliance") {
    return "Compliance";
  }
  return stage.replaceAll("_", " ");
}

function formatScore(score: number): string {
  return `${Math.round(Math.max(0, Math.min(score, 1)) * 100)}%`;
}

function boundedDisplay(value: string): string {
  if (value.length <= MAX_EXCERPT_DISPLAY_CHARS) {
    return value;
  }
  return `${value.slice(0, MAX_EXCERPT_DISPLAY_CHARS).trimEnd()}...`;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
