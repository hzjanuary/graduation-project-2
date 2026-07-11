"""Tests for the LangGraph runtime graph skeleton."""

import pytest
from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph

from app.models.enums import WorkflowStatus
from app.runtime import (
    RUNTIME_STAGES,
    RuntimeNodeHandler,
    RuntimeStage,
    RuntimeStatePayload,
    RuntimeWorkflowState,
    build_workflow_graph,
    runtime_graph_topology,
    runtime_stage_sequence,
    validate_runtime_node_handlers,
)
from app.workflows.schemas import WorkflowType


def _passthrough_handler(stage: RuntimeStage) -> RuntimeNodeHandler:
    def handler(state: RuntimeWorkflowState) -> RuntimeWorkflowState:
        return state.model_copy(
            update={
                "current_stage": stage,
                "completed_stages": (*state.completed_stages, stage),
            },
        )

    return handler


def _node_handlers() -> dict[RuntimeStage, RuntimeNodeHandler]:
    return {stage: _passthrough_handler(stage) for stage in RUNTIME_STAGES}


def _runtime_payload() -> RuntimeStatePayload:
    return {
        "workflow_id": "workflow-001",
        "workflow_type": WorkflowType.PROCUREMENT_QUOTATION.value,
        "status": WorkflowStatus.CREATED.value,
        "request": {"raw_text": "Need 50 business laptops."},
    }


def test_runtime_graph_module_imports_langgraph() -> None:
    graph = build_workflow_graph(_node_handlers())

    assert isinstance(graph, CompiledStateGraph)


def test_runtime_stage_sequence_matches_spec_006_order() -> None:
    assert runtime_stage_sequence() == (
        RuntimeStage.PLANNER,
        RuntimeStage.RETRIEVAL,
        RuntimeStage.QUOTATION,
        RuntimeStage.COMPLIANCE,
        RuntimeStage.VALIDATION,
        RuntimeStage.APPROVAL,
        RuntimeStage.EMAIL_PREPARATION,
    )


def test_runtime_graph_topology_is_linear() -> None:
    assert runtime_graph_topology() == (
        (START, "planner"),
        ("planner", "retrieval"),
        ("retrieval", "quotation"),
        ("quotation", "compliance"),
        ("compliance", "validation"),
        ("validation", "approval"),
        ("approval", "email_preparation"),
        ("email_preparation", END),
    )


def test_validate_runtime_node_handlers_requires_every_stage() -> None:
    handlers = _node_handlers()
    handlers.pop(RuntimeStage.RETRIEVAL)

    with pytest.raises(ValueError, match="missing: retrieval"):
        validate_runtime_node_handlers(handlers)


def test_build_workflow_graph_contains_expected_nodes_and_edges() -> None:
    graph = build_workflow_graph(_node_handlers())
    drawable_graph = graph.get_graph()

    assert set(drawable_graph.nodes) == {
        START,
        "planner",
        "retrieval",
        "quotation",
        "compliance",
        "validation",
        "approval",
        "email_preparation",
        END,
    }
    assert {(edge.source, edge.target) for edge in drawable_graph.edges} == set(
        runtime_graph_topology()
    )


def test_compiled_workflow_graph_invokes_injected_handlers_in_order() -> None:
    graph = build_workflow_graph(_node_handlers())

    result = graph.invoke(_runtime_payload())

    assert result["current_stage"] == RuntimeStage.EMAIL_PREPARATION.value
    assert result["completed_stages"] == [
        "planner",
        "retrieval",
        "quotation",
        "compliance",
        "validation",
        "approval",
        "email_preparation",
    ]
