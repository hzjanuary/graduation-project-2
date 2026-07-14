"""Tests for LLM provider client error mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.llm.clients import GeminiLLMClient, GroqLLMClient, OllamaLLMClient
from app.llm.clients.http import HTTPResponse, HTTPTimeoutError, HTTPTransportError
from app.llm.contracts import (
    LLMChatMessage,
    LLMChatRequest,
    LLMErrorCategory,
    LLMMessageRole,
    LLMResponseFormat,
)
from app.llm.errors import LLMConfigurationError, LLMProviderError


@dataclass
class CapturedRequest:
    url: str
    headers: dict[str, str]
    payload: dict[str, Any]
    timeout_seconds: int


@dataclass
class FakeTransport:
    responses: list[HTTPResponse | Exception]
    requests: list[CapturedRequest] = field(default_factory=list)

    async def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> HTTPResponse:
        self.requests.append(
            CapturedRequest(
                url=url,
                headers=headers,
                payload=payload,
                timeout_seconds=timeout_seconds,
            ),
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def request() -> LLMChatRequest:
    return LLMChatRequest(
        messages=(LLMChatMessage(role=LLMMessageRole.USER, content="hello"),),
        request_id="request-error",
    )


@pytest.mark.parametrize(
    "client",
    [
        GroqLLMClient(api_key="", model="llama"),
        GeminiLLMClient(api_key="", model="gemini"),
    ],
)
async def test_remote_clients_require_api_key(client: object) -> None:
    with pytest.raises(LLMConfigurationError) as exc_info:
        await client.complete(request())  # type: ignore[attr-defined]

    assert exc_info.value.category is LLMErrorCategory.CONFIGURATION
    assert "API key" in str(exc_info.value)


def test_ollama_rejects_invalid_base_url() -> None:
    client = OllamaLLMClient(base_url="not-a-url", model="llama3.1")

    with pytest.raises(LLMConfigurationError) as exc_info:
        client.validate_ready()

    assert exc_info.value.category is LLMErrorCategory.CONFIGURATION


@pytest.mark.parametrize(
    ("status_code", "category"),
    [
        (401, LLMErrorCategory.AUTHENTICATION),
        (403, LLMErrorCategory.AUTHENTICATION),
        (408, LLMErrorCategory.TIMEOUT),
        (429, LLMErrorCategory.RATE_LIMIT),
        (400, LLMErrorCategory.INVALID_RESPONSE),
        (422, LLMErrorCategory.INVALID_RESPONSE),
        (500, LLMErrorCategory.UNAVAILABLE),
        (503, LLMErrorCategory.UNAVAILABLE),
        (418, LLMErrorCategory.UNKNOWN),
    ],
)
async def test_http_statuses_map_to_safe_categories(
    status_code: int,
    category: LLMErrorCategory,
) -> None:
    transport = FakeTransport(
        responses=[
            HTTPResponse(
                status_code=status_code,
                payload={"error": {"message": "provider said no"}},
            ),
        ],
    )
    client = GroqLLMClient(
        api_key="super-secret-api-key",
        model="llama",
        transport=transport,
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await client.complete(request())

    assert exc_info.value.category is category
    assert "super-secret-api-key" not in str(exc_info.value)
    assert "super-secret-api-key" not in str(exc_info.value.safe_details())


async def test_transport_timeout_maps_to_timeout_category() -> None:
    transport = FakeTransport(responses=[HTTPTimeoutError("timed out")])
    client = GroqLLMClient(api_key="key", model="llama", transport=transport)

    with pytest.raises(LLMProviderError) as exc_info:
        await client.complete(request())

    assert exc_info.value.category is LLMErrorCategory.TIMEOUT


async def test_transport_error_maps_to_unavailable_category() -> None:
    transport = FakeTransport(responses=[HTTPTransportError("connection failed")])
    client = GroqLLMClient(api_key="key", model="llama", transport=transport)

    with pytest.raises(LLMProviderError) as exc_info:
        await client.complete(request())

    assert exc_info.value.category is LLMErrorCategory.UNAVAILABLE


async def test_malformed_provider_response_maps_to_invalid_response() -> None:
    transport = FakeTransport(
        responses=[
            HTTPResponse(status_code=200, payload={"choices": []}),
        ],
    )
    client = GroqLLMClient(api_key="key", model="llama", transport=transport)

    with pytest.raises(LLMProviderError) as exc_info:
        await client.complete(request())

    assert exc_info.value.category is LLMErrorCategory.INVALID_RESPONSE


async def test_invalid_structured_json_maps_to_invalid_response() -> None:
    transport = FakeTransport(
        responses=[
            HTTPResponse(
                status_code=200,
                payload={
                    "id": "response-1",
                    "model": "llama",
                    "choices": [
                        {"message": {"content": "not json"}, "finish_reason": "stop"},
                    ],
                },
            ),
        ],
    )
    client = GroqLLMClient(api_key="key", model="llama", transport=transport)

    with pytest.raises(LLMProviderError) as exc_info:
        await client.complete(
            LLMChatRequest(
                messages=(LLMChatMessage(role=LLMMessageRole.USER, content="json"),),
                response_format=LLMResponseFormat.JSON_OBJECT,
                structured_json=True,
            ),
        )

    assert exc_info.value.category is LLMErrorCategory.INVALID_RESPONSE
