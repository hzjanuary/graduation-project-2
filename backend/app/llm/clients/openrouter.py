"""OpenRouter LLM client."""

from __future__ import annotations

from app.llm.clients.http import AsyncJSONHTTPTransport
from app.llm.clients.openai_compatible import OpenAICompatibleLLMClient
from app.llm.contracts import LLMProvider


class OpenRouterLLMClient(OpenAICompatibleLLMClient):
    """OpenRouter client using the OpenAI-like chat completions API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        endpoint_url: str = "https://openrouter.ai/api/v1/chat/completions",
        transport: AsyncJSONHTTPTransport | None = None,
        default_timeout_seconds: int = 30,
    ) -> None:
        super().__init__(
            provider=LLMProvider.OPENROUTER,
            api_key=api_key,
            model=model,
            endpoint_url=endpoint_url,
            transport=transport,
            default_timeout_seconds=default_timeout_seconds,
        )
