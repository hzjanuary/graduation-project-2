"""Tests for deterministic fake LLM client behavior."""

from app.llm.clients import FakeLLMClient, LLMClient
from app.llm.contracts import (
    LLMChatMessage,
    LLMChatRequest,
    LLMMessageRole,
    LLMProvider,
    LLMResponseFormat,
)


async def test_fake_client_conforms_to_client_protocol() -> None:
    client = FakeLLMClient()

    assert isinstance(client, LLMClient)
    assert client.provider is LLMProvider.FAKE
    client.validate_ready()


async def test_fake_client_returns_deterministic_text_response() -> None:
    client = FakeLLMClient(model="fake-model")
    request = LLMChatRequest(
        messages=(
            LLMChatMessage(role=LLMMessageRole.USER, content="Summarize RFQ-001"),
        ),
        request_id="request-1",
    )

    first_response = await client.complete(request)
    second_response = await client.complete(request)

    assert first_response == second_response
    assert first_response.provider is LLMProvider.FAKE
    assert first_response.model == "fake-model"
    assert first_response.request_id == "fake:request-1"
    assert "Summarize RFQ-001" in first_response.content
    assert first_response.metadata == {
        "fake": True,
        "provider_response_id": "fake:request-1",
    }


async def test_fake_client_returns_structured_json_when_requested() -> None:
    client = FakeLLMClient()
    request = LLMChatRequest(
        messages=(
            LLMChatMessage(role=LLMMessageRole.SYSTEM, content="Return JSON."),
            LLMChatMessage(role=LLMMessageRole.USER, content="Classify request."),
        ),
        response_format=LLMResponseFormat.JSON_OBJECT,
        structured_json=True,
    )

    response = await client.complete(request)

    assert response.structured_json == {
        "last_user_message": "Classify request.",
        "message_count": 2,
        "provider": "fake",
        "status": "deterministic",
    }
    assert response.structured_metadata is not None
    assert response.structured_metadata.schema_name == "json_object"
