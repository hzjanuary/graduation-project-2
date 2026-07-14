"""Deterministic offline fake LLM client."""

from __future__ import annotations

import json

from app.llm.clients.base import build_chat_response, resolve_model, usage_from_values
from app.llm.contracts import (
    LLMChatRequest,
    LLMChatResponse,
    LLMFinishReason,
    LLMMessageRole,
    LLMProvider,
)


class FakeLLMClient:
    """Deterministic fake provider for tests and no-key local development."""

    def __init__(self, *, model: str = "fake-deterministic-model") -> None:
        self._model = model

    @property
    def provider(self) -> LLMProvider:
        """Return this client's provider identifier."""
        return LLMProvider.FAKE

    @property
    def model(self) -> str:
        """Return this client's configured default model."""
        return self._model

    def validate_ready(self) -> None:
        """Fake provider is always ready and never needs credentials."""

    async def complete(self, request: LLMChatRequest) -> LLMChatResponse:
        """Return deterministic content derived from the request shape."""
        model = resolve_model(
            provider=self.provider,
            configured_model=self.model,
            request=request,
        )
        content = self._content_for_request(request)
        response_id = (
            f"fake:{request.request_id}" if request.request_id else "fake:deterministic"
        )
        return build_chat_response(
            provider=self.provider,
            model=model,
            content=content,
            request=request,
            finish_reason=LLMFinishReason.STOP,
            usage=usage_from_values(
                prompt_tokens=sum(
                    len(message.content.split()) for message in request.messages
                ),
                completion_tokens=len(content.split()),
            ),
            response_id=response_id,
            metadata={"fake": True},
        )

    def _content_for_request(self, request: LLMChatRequest) -> str:
        if request.structured_json:
            payload = {
                "provider": self.provider.value,
                "status": "deterministic",
                "message_count": len(request.messages),
                "last_user_message": self._last_user_message(request)[:200],
            }
            return json.dumps(payload, sort_keys=True)
        return (
            "Deterministic fake response: "
            f"{len(request.messages)} messages; "
            f"last_user={self._last_user_message(request)[:200]}"
        )

    def _last_user_message(self, request: LLMChatRequest) -> str:
        for message in reversed(request.messages):
            if message.role is LLMMessageRole.USER:
                return message.content
        return request.messages[-1].content
