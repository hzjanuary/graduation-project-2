"""Provider-independent schemas for reference price research.

Price research output is review evidence only. It is never an approved
quotation, stock promise, delivery promise, or authorization to respond to a
customer without human approval.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from math import isfinite
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_TEXT_LENGTH = 1000
MAX_REQUEST_TEXT_LENGTH = 5000
MAX_CONTEXT_KEYS = 40
MAX_CONTEXT_DEPTH = 4
MAX_CONTEXT_STRING_LENGTH = 1000
MAX_CONTEXT_LIST_LENGTH = 50
MAX_ADDONS = 20
MAX_WARNINGS = 20
MAX_SOURCES = 20
MAX_REFERENCE_PRICES = 20
MAX_URL_LENGTH = 1000

SENSITIVE_METADATA_TOKENS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "chain_of_thought",
    "cookie",
    "jwt",
    "password",
    "provider_payload",
    "raw_prompt",
    "raw_provider",
    "secret",
    "token",
)


class PriceResearchSourceType(StrEnum):
    """Supported normalized source categories for reference price evidence."""

    INTERNAL_CATALOG = "internal_catalog"
    RAG = "rag"
    EXTERNAL_WEB = "external_web"
    MANUAL = "manual"
    FAKE = "fake"


JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


def validate_json_context(value: dict[str, Any], field_name: str) -> dict[str, Any]:
    """Validate bounded JSON-compatible context without sensitive keys."""
    _validate_json_value(value, field_name=field_name, depth=0)
    return value


def _validate_json_value(value: Any, *, field_name: str, depth: int) -> None:
    if depth > MAX_CONTEXT_DEPTH:
        raise ValueError(f"{field_name} exceeds maximum nesting depth")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{field_name} contains a non-finite number")
        return
    if isinstance(value, str):
        if len(value) > MAX_CONTEXT_STRING_LENGTH:
            raise ValueError(f"{field_name} contains an overlong string")
        return
    if isinstance(value, list):
        if len(value) > MAX_CONTEXT_LIST_LENGTH:
            raise ValueError(f"{field_name} contains too many list items")
        for item in value:
            _validate_json_value(item, field_name=field_name, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_CONTEXT_KEYS:
            raise ValueError(f"{field_name} contains too many keys")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{field_name} keys must be strings")
            normalized_key = key.strip().lower()
            if not normalized_key or len(normalized_key) > 120:
                raise ValueError(f"{field_name} keys must be bounded strings")
            if any(token in normalized_key for token in SENSITIVE_METADATA_TOKENS):
                raise ValueError(f"{field_name} contains sensitive metadata key")
            _validate_json_value(item, field_name=field_name, depth=depth + 1)
        return
    raise ValueError(f"{field_name} must be JSON-compatible")


def _strip_required_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("value must not be blank")
    return stripped


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime values must be timezone-aware")
    return value


class PriceResearchRequest(BaseModel):
    """Provider-independent input for reference price research."""

    model_config = ConfigDict(frozen=True)

    item_name: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    normalized_item_name: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    quantity: int = Field(gt=0)
    region: str = Field(min_length=1, max_length=120)
    currency: str = Field(min_length=3, max_length=3)
    customer_context: dict[str, Any] = Field(default_factory=dict)
    requested_addons: tuple[str, ...] = Field(
        default_factory=tuple,
        max_length=MAX_ADDONS,
    )
    workflow_id: UUID | None = None
    request_text: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_REQUEST_TEXT_LENGTH,
    )

    @field_validator("item_name", "normalized_item_name", "region")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        """Strip required strings and reject whitespace-only values."""
        return _strip_required_text(value)

    @field_validator("request_text")
    @classmethod
    def strip_optional_request_text(cls, value: str | None) -> str | None:
        """Normalize optional request text without retaining blank values."""
        return _normalize_optional_text(value)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Normalize ISO-like currency values to uppercase."""
        return str(value).strip().upper()

    @field_validator("customer_context")
    @classmethod
    def validate_customer_context(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Ensure customer context remains bounded and JSON safe."""
        return validate_json_context(value, "customer_context")

    @field_validator("requested_addons", mode="before")
    @classmethod
    def coerce_requested_addons(
        cls,
        value: tuple[str, ...] | list[str],
    ) -> tuple[str, ...] | list[str]:
        """Accept list input while storing requested add-ons immutably."""
        return tuple(value) if isinstance(value, list) else value

    @field_validator("requested_addons")
    @classmethod
    def normalize_requested_addons(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Lowercase, bound, and de-duplicate requested add-ons."""
        seen: set[str] = set()
        normalized: list[str] = []
        for addon in value:
            stripped = addon.strip().lower()
            if not stripped or len(stripped) > 120:
                raise ValueError("requested_addons must contain bounded values")
            if any(token in stripped for token in SENSITIVE_METADATA_TOKENS):
                raise ValueError("requested_addons must not contain sensitive markers")
            if stripped in seen:
                continue
            seen.add(stripped)
            normalized.append(stripped)
        return tuple(normalized)


class PriceResearchSource(BaseModel):
    """A normalized source supporting reference price evidence."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    url: str | None = Field(default=None, min_length=1, max_length=MAX_URL_LENGTH)
    snippet: str | None = Field(default=None, min_length=1, max_length=MAX_TEXT_LENGTH)
    observed_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    retrieved_at: datetime
    source_type: PriceResearchSourceType
    confidence: float = Field(ge=0, le=1)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        """Strip source title."""
        return _strip_required_text(value)

    @field_validator("url", "snippet")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        """Strip optional strings."""
        return _normalize_optional_text(value)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_optional_currency(cls, value: str | None) -> str | None:
        """Normalize optional source currency."""
        if value is None:
            return None
        return str(value).strip().upper()

    @field_validator("retrieved_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Require timezone-aware source retrieval timestamps."""
        return _require_timezone(value)


class ReferencePrice(BaseModel):
    """A reference price candidate, not a final quote."""

    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    unit: str | None = Field(default=None, min_length=1, max_length=120)
    quantity_basis: int | None = Field(default=None, gt=0)
    source_index: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, min_length=1, max_length=MAX_TEXT_LENGTH)

    @field_validator("label")
    @classmethod
    def strip_label(cls, value: str) -> str:
        """Strip reference price label."""
        return _strip_required_text(value)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_optional_currency(cls, value: str | None) -> str | None:
        """Normalize optional reference price currency."""
        if value is None:
            return None
        return str(value).strip().upper()

    @field_validator("unit", "notes")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        """Strip optional reference price strings."""
        return _normalize_optional_text(value)


class PriceResearchResult(BaseModel):
    """Provider-independent reference price evidence result.

    `is_final_quote` is intentionally constrained to false. Final quotation
    requires the existing human approval and resume lifecycle.
    """

    model_config = ConfigDict(frozen=True)

    item_name: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    normalized_item_name: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    quantity: int = Field(gt=0)
    region: str = Field(min_length=1, max_length=120)
    currency: str = Field(min_length=3, max_length=3)
    reference_prices: tuple[ReferencePrice, ...] = Field(
        default_factory=tuple,
        max_length=MAX_REFERENCE_PRICES,
    )
    sources: tuple[PriceResearchSource, ...] = Field(
        default_factory=tuple,
        max_length=MAX_SOURCES,
    )
    confidence: float = Field(ge=0, le=1)
    retrieved_at: datetime
    warnings: tuple[str, ...] = Field(default_factory=tuple, max_length=MAX_WARNINGS)
    provider: str = Field(min_length=1, max_length=120)
    is_final_quote: bool = False
    evidence_label: str = Field(
        default="reference_price_research",
        min_length=1,
        max_length=120,
    )

    @field_validator("item_name", "normalized_item_name", "region", "provider")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        """Strip required strings and reject whitespace-only values."""
        return _strip_required_text(value)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Normalize result currency."""
        return str(value).strip().upper()

    @field_validator("reference_prices", mode="before")
    @classmethod
    def coerce_reference_prices(
        cls,
        value: tuple[ReferencePrice, ...] | list[ReferencePrice],
    ) -> tuple[ReferencePrice, ...] | list[ReferencePrice]:
        """Accept list input while storing reference prices immutably."""
        return tuple(value) if isinstance(value, list) else value

    @field_validator("sources", mode="before")
    @classmethod
    def coerce_sources(
        cls,
        value: tuple[PriceResearchSource, ...] | list[PriceResearchSource],
    ) -> tuple[PriceResearchSource, ...] | list[PriceResearchSource]:
        """Accept list input while storing sources immutably."""
        return tuple(value) if isinstance(value, list) else value

    @field_validator("warnings", mode="before")
    @classmethod
    def coerce_warnings(
        cls,
        value: tuple[str, ...] | list[str],
    ) -> tuple[str, ...] | list[str]:
        """Accept list input while storing warnings immutably."""
        return tuple(value) if isinstance(value, list) else value

    @field_validator("warnings")
    @classmethod
    def normalize_warnings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Strip, bound, and de-duplicate warnings."""
        seen: set[str] = set()
        normalized: list[str] = []
        for warning in value:
            stripped = warning.strip()
            if not stripped or len(stripped) > MAX_TEXT_LENGTH:
                raise ValueError("warnings must contain bounded non-empty values")
            lowered = stripped.lower()
            if any(token in lowered for token in SENSITIVE_METADATA_TOKENS):
                raise ValueError("warnings must not contain sensitive markers")
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(stripped)
        return tuple(normalized)

    @field_validator("retrieved_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Require timezone-aware result retrieval timestamp."""
        return _require_timezone(value)

    @model_validator(mode="after")
    def validate_reference_result(self) -> PriceResearchResult:
        """Validate result consistency and final-quote safety."""
        if self.is_final_quote:
            raise ValueError("price research result must not be a final quote")
        for reference_price in self.reference_prices:
            if (
                reference_price.source_index is not None
                and reference_price.source_index >= len(self.sources)
            ):
                raise ValueError("source_index must refer to an existing source")
        if not self.reference_prices and not self.warnings:
            raise ValueError("empty reference_prices require at least one warning")
        return self
