"""LangGraph workflow graph skeleton for runtime orchestration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.runtime.schemas import RUNTIME_STAGES, RuntimeStage, RuntimeWorkflowState


class RuntimeStatePayload(TypedDict, total=False):
    """Dict state payload accepted by LangGraph and parsed by runtime schemas."""

    workflow_id: str
    workflow_type: str
    domain: str | None
    status: str
    request: dict[str, Any]
    metadata: dict[str, Any]
    customer: dict[str, Any]
    items: list[dict[str, Any]]
    current_stage: str | None
    completed_stages: list[str]
    failed_stage: str | None
    runtime_context: dict[str, Any]
    stage_outputs: dict[str, dict[str, Any]]
    outputs: dict[str, Any]
    steps: list[dict[str, Any]]
    error: dict[str, Any] | None
    retry_count: int
    events: list[dict[str, Any]]


type RuntimeNodeHandler = Callable[[RuntimeWorkflowState], RuntimeWorkflowState]
type RuntimeNodeHandlers = Mapping[RuntimeStage, RuntimeNodeHandler]
type RuntimeGraphEdge = tuple[str, str]
type CompiledWorkflowGraph = CompiledStateGraph[
    RuntimeStatePayload,
    None,
    RuntimeStatePayload,
    RuntimeStatePayload,
]


def runtime_stage_sequence() -> tuple[RuntimeStage, ...]:
    """Return the deterministic runtime stage sequence."""
    return RUNTIME_STAGES


def runtime_graph_topology() -> tuple[RuntimeGraphEdge, ...]:
    """Return the linear runtime graph topology as edge pairs."""
    stages = runtime_stage_sequence()
    return (
        (START, stages[0].value),
        *(
            (from_stage.value, to_stage.value)
            for from_stage, to_stage in zip(stages, stages[1:], strict=False)
        ),
        (stages[-1].value, END),
    )


def validate_runtime_node_handlers(
    node_handlers: RuntimeNodeHandlers,
) -> None:
    """Raise when node handlers do not cover every runtime stage."""
    expected_stages = set(runtime_stage_sequence())
    provided_stages = set(node_handlers)
    missing_stages = expected_stages - provided_stages
    extra_stages = provided_stages - expected_stages

    if missing_stages or extra_stages:
        missing = ", ".join(stage.value for stage in sorted(missing_stages))
        extra = ", ".join(stage.value for stage in sorted(extra_stages))
        detail_parts = []
        if missing:
            detail_parts.append(f"missing: {missing}")
        if extra:
            detail_parts.append(f"extra: {extra}")
        raise ValueError(
            "Runtime node handlers must match runtime stages "
            f"({'; '.join(detail_parts)})",
        )


def build_workflow_graph(
    node_handlers: RuntimeNodeHandlers,
) -> CompiledWorkflowGraph:
    """Build and compile the deterministic workflow graph skeleton."""
    validate_runtime_node_handlers(node_handlers)

    graph: StateGraph[
        RuntimeStatePayload,
        None,
        RuntimeStatePayload,
        RuntimeStatePayload,
    ] = StateGraph(RuntimeStatePayload)
    for stage in runtime_stage_sequence():
        graph.add_node(
            stage.value,
            cast(Any, _wrap_runtime_node_handler(node_handlers[stage])),
        )

    for source, target in runtime_graph_topology():
        graph.add_edge(source, target)

    return graph.compile()


def _wrap_runtime_node_handler(
    handler: RuntimeNodeHandler,
) -> Callable[[RuntimeStatePayload], RuntimeStatePayload]:
    def wrapped_handler(state: RuntimeStatePayload) -> RuntimeStatePayload:
        runtime_state = RuntimeWorkflowState.model_validate(state)
        next_state = handler(runtime_state)
        return cast(RuntimeStatePayload, next_state.model_dump(mode="json"))

    return wrapped_handler


__all__ = [
    "RuntimeGraphEdge",
    "RuntimeNodeHandler",
    "RuntimeNodeHandlers",
    "RuntimeStatePayload",
    "CompiledWorkflowGraph",
    "build_workflow_graph",
    "runtime_graph_topology",
    "runtime_stage_sequence",
    "validate_runtime_node_handlers",
]
