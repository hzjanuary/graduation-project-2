"""Runtime RAG grounding adapter for citation-aware workflow stages."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.knowledge.schemas import (
    KnowledgeCitation,
    KnowledgeDocumentSourceType,
    KnowledgeRetrievalResult,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.runtime.schemas import RuntimeStage, RuntimeWorkflowState

KNOWLEDGE_GROUNDING_STARTED_EVENT = "knowledge.grounding.started"
KNOWLEDGE_GROUNDING_COMPLETED_EVENT = "knowledge.grounding.completed"
KNOWLEDGE_GROUNDING_FAILED_EVENT = "knowledge.grounding.failed"

RAG_SUPPORTED_STAGES: tuple[RuntimeStage, ...] = (
    RuntimeStage.COMPLIANCE,
    RuntimeStage.VALIDATION,
    RuntimeStage.APPROVAL,
)

DEFAULT_RAG_TOP_K = 3
DEFAULT_RAG_MINIMUM_SCORE = 0.0
DEFAULT_RAG_MAX_CONTEXT_CHARS = 3000
DEFAULT_RAG_EVENT_PAYLOAD_MAX_CHARS = 2000


class KnowledgeRetrievalServiceProtocol(Protocol):
    """Narrow retrieval service protocol required by runtime grounding."""

    def search(
        self,
        request: KnowledgeSearchRequest,
    ) -> Awaitable[KnowledgeSearchResponse]:
        """Search knowledge chunks and return provider-independent citations."""
        ...


class RAGGroundingResult(BaseModel):
    """Bounded runtime grounding result for one workflow stage."""

    model_config = ConfigDict(frozen=True)

    stage: RuntimeStage
    query_label: str = Field(min_length=1, max_length=120)
    result_count: int = Field(ge=0, le=20)
    citations: tuple[dict[str, Any], ...] = Field(default_factory=tuple, max_length=20)


class RuntimeRAGGroundingAdapter:
    """Retrieve and merge bounded evidence into runtime state."""

    def __init__(
        self,
        retrieval_service: KnowledgeRetrievalServiceProtocol,
        *,
        top_k: int = DEFAULT_RAG_TOP_K,
        minimum_score: float = DEFAULT_RAG_MINIMUM_SCORE,
        max_context_chars: int = DEFAULT_RAG_MAX_CONTEXT_CHARS,
        event_payload_max_chars: int = DEFAULT_RAG_EVENT_PAYLOAD_MAX_CHARS,
    ) -> None:
        if top_k < 1 or top_k > 20:
            raise ValueError("RAG top_k must be between 1 and 20")
        if minimum_score < 0.0 or minimum_score > 1.0:
            raise ValueError("RAG minimum_score must be between 0.0 and 1.0")
        if max_context_chars < 100 or max_context_chars > 20000:
            raise ValueError("RAG max_context_chars must be between 100 and 20000")
        if event_payload_max_chars < 100 or event_payload_max_chars > 10000:
            raise ValueError(
                "RAG event_payload_max_chars must be between 100 and 10000",
            )

        self._retrieval_service = retrieval_service
        self.top_k = top_k
        self.minimum_score = minimum_score
        self.max_context_chars = max_context_chars
        self.event_payload_max_chars = event_payload_max_chars

    def supports_stage(self, stage: RuntimeStage) -> bool:
        """Return whether a stage should receive retrieval grounding."""
        return stage in RAG_SUPPORTED_STAGES

    async def retrieve_stage_grounding(
        self,
        state: RuntimeWorkflowState,
        stage: RuntimeStage,
    ) -> RAGGroundingResult:
        """Retrieve bounded citations for one supported runtime stage."""
        if not self.supports_stage(stage):
            return RAGGroundingResult(
                stage=stage,
                query_label="unsupported_stage",
                result_count=0,
            )

        query_label, query, source_types = _stage_query(state, stage)
        response = await self._retrieval_service.search(
            KnowledgeSearchRequest(
                query=query,
                top_k=self.top_k,
                source_types=source_types,
                minimum_score=self.minimum_score,
            ),
        )
        citations = tuple(
            self._evidence_for_results(response.results, stage, query_label),
        )
        return RAGGroundingResult(
            stage=stage,
            query_label=query_label,
            result_count=len(citations),
            citations=citations,
        )

    def apply_grounding(
        self,
        state: RuntimeWorkflowState,
        result: RAGGroundingResult,
        *,
        include_stage_output: bool = True,
    ) -> RuntimeWorkflowState:
        """Attach bounded citation summaries to runtime context and outputs."""
        rag_context = _runtime_rag_context(state)
        stage_payload = {
            "stage": result.stage.value,
            "query_label": result.query_label,
            "result_count": result.result_count,
            "citations": [dict(citation) for citation in result.citations],
        }
        rag_context["stages"][result.stage.value] = stage_payload

        outputs = dict(state.outputs)
        evidence_outputs = _dict_output(outputs.get("evidence"))
        evidence_outputs[result.stage.value] = [
            dict(citation) for citation in result.citations
        ]
        outputs["evidence"] = evidence_outputs

        stage_outputs = {
            existing_stage: dict(output)
            for existing_stage, output in state.stage_outputs.items()
        }
        if include_stage_output:
            existing_output = dict(stage_outputs.get(result.stage, {}))
            existing_output["evidence"] = [
                dict(citation) for citation in result.citations
            ]
            existing_output["evidence_count"] = result.result_count
            existing_output["evidence_query_label"] = result.query_label
            stage_outputs[result.stage] = existing_output

        runtime_context = dict(state.runtime_context)
        runtime_context["rag"] = rag_context
        return state.model_copy(
            update={
                "runtime_context": runtime_context,
                "outputs": outputs,
                "stage_outputs": stage_outputs,
            },
        )

    def failure_context(
        self,
        state: RuntimeWorkflowState,
        stage: RuntimeStage,
        *,
        error_type: str,
    ) -> RuntimeWorkflowState:
        """Record a safe degraded grounding marker without failing runtime."""
        rag_context = _runtime_rag_context(state)
        rag_context["stages"][stage.value] = {
            "stage": stage.value,
            "status": "failed",
            "result_count": 0,
            "error_type": error_type[:120],
        }
        runtime_context = dict(state.runtime_context)
        runtime_context["rag"] = rag_context
        return state.model_copy(update={"runtime_context": runtime_context})

    def event_payload(self, result: RAGGroundingResult) -> dict[str, Any]:
        """Return a bounded event payload for completed grounding."""
        citations = [dict(citation) for citation in result.citations]
        source_types = sorted(
            {
                str(citation["source_type"])
                for citation in citations
                if isinstance(citation.get("source_type"), str)
            },
        )
        return {
            "stage": result.stage.value,
            "top_k": self.top_k,
            "result_count": result.result_count,
            "citation_ids": [
                str(citation["citation_id"])
                for citation in citations
                if isinstance(citation.get("citation_id"), str)
            ],
            "source_types": source_types,
            "query_label": result.query_label,
        }

    def _evidence_for_results(
        self,
        results: tuple[KnowledgeRetrievalResult, ...],
        stage: RuntimeStage,
        query_label: str,
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        remaining_excerpt_chars = self.max_context_chars
        for result in results[: self.top_k]:
            if remaining_excerpt_chars <= 0:
                break
            citation = result.citation
            excerpt = citation.excerpt[:remaining_excerpt_chars].strip()
            if not excerpt:
                continue
            remaining_excerpt_chars -= len(excerpt)
            evidence.append(
                _evidence_payload_for_citation(
                    citation,
                    excerpt=excerpt,
                    stage=stage,
                    query_label=query_label,
                ),
            )
        return evidence


def _stage_query(
    state: RuntimeWorkflowState,
    stage: RuntimeStage,
) -> tuple[str, str, tuple[KnowledgeDocumentSourceType, ...]]:
    domain = _bounded_query_part(state.domain or "procurement")
    request_hint = _bounded_request_hint(state.request)
    if stage is RuntimeStage.COMPLIANCE:
        return (
            "compliance_policy_contract_checklist",
            (
                "procurement policy contract terms compliance checklist "
                f"domain {domain} request {request_hint}"
            ),
            (
                KnowledgeDocumentSourceType.POLICY,
                KnowledgeDocumentSourceType.CONTRACT,
                KnowledgeDocumentSourceType.COMPLIANCE_CHECKLIST,
            ),
        )
    if stage is RuntimeStage.VALIDATION:
        return (
            "finance_pricing_supplier_risk",
            (
                "pricing guideline supplier evaluation finance risk threshold "
                f"domain {domain} request {request_hint}"
            ),
            (
                KnowledgeDocumentSourceType.PRICING,
                KnowledgeDocumentSourceType.SUPPLIER_PROFILE,
                KnowledgeDocumentSourceType.POLICY,
            ),
        )
    if stage is RuntimeStage.APPROVAL:
        return (
            "approval_policy_contract_evidence",
            (
                "procurement policy contract terms approval evidence summary "
                f"domain {domain} request {request_hint}"
            ),
            (
                KnowledgeDocumentSourceType.POLICY,
                KnowledgeDocumentSourceType.CONTRACT,
                KnowledgeDocumentSourceType.PRICING,
                KnowledgeDocumentSourceType.COMPLIANCE_CHECKLIST,
            ),
        )
    return ("unsupported_stage", f"unsupported stage {stage.value}", ())


def _bounded_request_hint(request: dict[str, Any]) -> str:
    raw_text = request.get("raw_text")
    if isinstance(raw_text, str) and raw_text.strip():
        return _bounded_query_part(raw_text)
    return "procurement request"


def _bounded_query_part(value: str, *, limit: int = 300) -> str:
    return " ".join(value.split())[:limit]


def _runtime_rag_context(state: RuntimeWorkflowState) -> dict[str, Any]:
    existing = state.runtime_context.get("rag")
    if not isinstance(existing, dict):
        return {"enabled": True, "stages": {}}
    stages = existing.get("stages")
    if not isinstance(stages, dict):
        stages = {}
    return {
        "enabled": True,
        "stages": {
            str(stage): dict(payload)
            for stage, payload in stages.items()
            if isinstance(payload, dict)
        },
    }


def _dict_output(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): value for key, value in value.items()}


def _evidence_payload_for_citation(
    citation: KnowledgeCitation,
    *,
    excerpt: str,
    stage: RuntimeStage,
    query_label: str,
) -> dict[str, Any]:
    payload = citation.model_dump(mode="json")
    return {
        "citation_id": payload["citation_id"],
        "document_id": payload["document_id"],
        "document_title": payload["document_title"],
        "source_type": payload["source_type"],
        "citation_label": payload["citation_label"],
        "section": payload.get("section"),
        "page": payload.get("page"),
        "excerpt": excerpt,
        "relevance_score": payload["relevance_score"],
        "stage": stage.value,
        "reason": query_label,
    }


def runtime_state_with_grounding(
    payload: dict[str, Any],
    adapter: RuntimeRAGGroundingAdapter,
    result: RAGGroundingResult,
    *,
    include_stage_output: bool = True,
) -> dict[str, Any]:
    """Return a JSON payload copy with grounding applied."""
    state = RuntimeWorkflowState.model_validate(payload)
    grounded_state = adapter.apply_grounding(
        state,
        result,
        include_stage_output=include_stage_output,
    )
    return grounded_state.model_dump(mode="json")


__all__ = [
    "DEFAULT_RAG_EVENT_PAYLOAD_MAX_CHARS",
    "DEFAULT_RAG_MAX_CONTEXT_CHARS",
    "DEFAULT_RAG_MINIMUM_SCORE",
    "DEFAULT_RAG_TOP_K",
    "KNOWLEDGE_GROUNDING_COMPLETED_EVENT",
    "KNOWLEDGE_GROUNDING_FAILED_EVENT",
    "KNOWLEDGE_GROUNDING_STARTED_EVENT",
    "KnowledgeRetrievalServiceProtocol",
    "RAGGroundingResult",
    "RAG_SUPPORTED_STAGES",
    "RuntimeRAGGroundingAdapter",
    "runtime_state_with_grounding",
]
