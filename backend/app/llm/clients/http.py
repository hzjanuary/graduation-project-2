"""Small injectable JSON HTTP transport for LLM provider clients."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field


class HTTPResponse(BaseModel):
    """JSON HTTP response returned by injectable transports."""

    model_config = ConfigDict(frozen=True)

    status_code: int = Field(ge=100, le=599)
    payload: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)


class HTTPTransportError(Exception):
    """Raised when a transport cannot reach a provider."""


class HTTPTimeoutError(HTTPTransportError):
    """Raised when a provider request times out."""


class AsyncJSONHTTPTransport(Protocol):
    """Async JSON POST transport protocol used by provider clients."""

    async def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> HTTPResponse:
        """POST JSON and return parsed JSON response metadata."""
        ...


class UrllibAsyncJSONHTTPTransport:
    """Stdlib JSON transport used outside tests.

    Tests inject fake transports, so this implementation is not exercised
    against live providers by the automated suite.
    """

    async def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> HTTPResponse:
        """POST JSON using urllib in a thread to avoid blocking the event loop."""
        return await asyncio.to_thread(
            self._post_json,
            url=url,
            headers=headers,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )

    def _post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> HTTPResponse:
        encoded_payload = json.dumps(payload).encode("utf-8")
        request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **headers,
        }
        request = Request(
            url,
            data=encoded_payload,
            headers=request_headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return HTTPResponse(
                    status_code=response.status,
                    payload=_decode_json_object(body),
                    headers=dict(response.headers.items()),
                )
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return HTTPResponse(
                status_code=exc.code,
                payload=_decode_json_object(body),
                headers=dict(exc.headers.items()) if exc.headers else {},
            )
        except TimeoutError as exc:
            raise HTTPTimeoutError("provider request timed out") from exc
        except URLError as exc:
            raise HTTPTransportError("provider request failed") from exc


def _decode_json_object(body: str) -> dict[str, Any]:
    if not body:
        return {}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body[:500]}
    return parsed if isinstance(parsed, dict) else {"value": parsed}
