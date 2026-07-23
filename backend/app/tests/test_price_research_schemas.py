"""Tests for provider-independent reference price research schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.price_research import (
    PriceResearchRequest,
    PriceResearchResult,
    PriceResearchSource,
    PriceResearchSourceType,
    ReferencePrice,
)


def _retrieved_at() -> datetime:
    return datetime(2026, 7, 24, 12, 0, tzinfo=UTC)


def _source() -> PriceResearchSource:
    return PriceResearchSource(
        title="Manual laptop reference",
        url="https://example.test/laptops",
        snippet="Bounded source summary.",
        observed_price=Decimal("12000000"),
        currency="vnd",
        retrieved_at=_retrieved_at(),
        source_type=PriceResearchSourceType.MANUAL,
        confidence=0.8,
    )


def test_valid_request_normalizes_safe_fields() -> None:
    request = PriceResearchRequest.model_validate(
        {
            "item_name": "  laptop  ",
            "normalized_item_name": " Standard business laptop ",
            "quantity": 20,
            "region": " vn ",
            "currency": "vnd",
            "customer_context": {
                "customer_name": "Telegram Customer",
                "demo": True,
            },
            "requested_addons": ["Office_365", "office_365", " microsoft_365 "],
            "workflow_id": uuid4(),
            "request_text": " quote for 20 laptops ",
        },
    )

    assert request.item_name == "laptop"
    assert request.normalized_item_name == "Standard business laptop"
    assert request.currency == "VND"
    assert request.requested_addons == ("office_365", "microsoft_365")
    assert request.request_text == "quote for 20 laptops"


def test_request_rejects_empty_item_name() -> None:
    with pytest.raises(ValidationError):
        PriceResearchRequest(
            item_name="   ",
            normalized_item_name="Standard business laptop",
            quantity=20,
            region="VN",
            currency="VND",
        )


def test_request_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValidationError):
        PriceResearchRequest(
            item_name="laptop",
            normalized_item_name="Standard business laptop",
            quantity=0,
            region="VN",
            currency="VND",
        )


def test_request_rejects_sensitive_customer_context() -> None:
    with pytest.raises(ValidationError, match="sensitive"):
        PriceResearchRequest(
            item_name="laptop",
            normalized_item_name="Standard business laptop",
            quantity=20,
            region="VN",
            currency="VND",
            customer_context={"api_key": "not-allowed"},
        )


def test_valid_source_schema_requires_bounded_safe_values() -> None:
    source = _source()

    assert source.currency == "VND"
    assert source.source_type is PriceResearchSourceType.MANUAL
    assert source.confidence == 0.8


def test_source_rejects_confidence_outside_range() -> None:
    with pytest.raises(ValidationError):
        PriceResearchSource(
            title="Bad source",
            retrieved_at=_retrieved_at(),
            source_type=PriceResearchSourceType.EXTERNAL_WEB,
            confidence=1.1,
        )


def test_source_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        PriceResearchSource(
            title="Naive timestamp",
            retrieved_at=datetime(2026, 7, 24, 12, 0),
            source_type=PriceResearchSourceType.FAKE,
            confidence=0.5,
        )


def test_result_rejects_final_quote_flag() -> None:
    with pytest.raises(ValidationError, match="final quote"):
        PriceResearchResult(
            item_name="laptop",
            normalized_item_name="Standard business laptop",
            quantity=20,
            region="VN",
            currency="VND",
            reference_prices=(
                ReferencePrice(label="Reference unit price", source_index=0),
            ),
            sources=(_source(),),
            confidence=0.7,
            retrieved_at=_retrieved_at(),
            warnings=(),
            provider="manual",
            is_final_quote=True,
        )


def test_result_validates_reference_source_index() -> None:
    with pytest.raises(ValidationError, match="source_index"):
        PriceResearchResult(
            item_name="laptop",
            normalized_item_name="Standard business laptop",
            quantity=20,
            region="VN",
            currency="VND",
            reference_prices=(
                ReferencePrice(label="Reference unit price", source_index=1),
            ),
            sources=(_source(),),
            confidence=0.7,
            retrieved_at=_retrieved_at(),
            warnings=(),
            provider="manual",
        )


def test_empty_reference_prices_are_allowed_with_warning() -> None:
    result = PriceResearchResult(
        item_name="laptop",
        normalized_item_name="Standard business laptop",
        quantity=20,
        region="VN",
        currency="vnd",
        reference_prices=(),
        sources=(),
        confidence=0,
        retrieved_at=_retrieved_at(),
        warnings=("No reference price found.",),
        provider="manual",
    )

    dumped = result.model_dump(mode="json")

    assert result.is_final_quote is False
    assert result.currency == "VND"
    assert result.evidence_label == "reference_price_research"
    assert dumped["warnings"] == ["No reference price found."]


def test_result_rejects_empty_reference_prices_without_warning() -> None:
    with pytest.raises(ValidationError, match="empty reference_prices"):
        PriceResearchResult(
            item_name="laptop",
            normalized_item_name="Standard business laptop",
            quantity=20,
            region="VN",
            currency="VND",
            reference_prices=(),
            sources=(),
            confidence=0,
            retrieved_at=_retrieved_at(),
            warnings=(),
            provider="manual",
        )


def test_public_schemas_do_not_include_raw_sensitive_payload_fields() -> None:
    result = PriceResearchResult(
        item_name="laptop",
        normalized_item_name="Standard business laptop",
        quantity=20,
        region="VN",
        currency="VND",
        reference_prices=(
            ReferencePrice(
                label="Reference unit price",
                amount=Decimal("12000000"),
                currency="vnd",
                unit="unit",
                quantity_basis=1,
                source_index=0,
                notes="Reference only.",
            ),
        ),
        sources=(_source(),),
        confidence=0.8,
        retrieved_at=_retrieved_at(),
        warnings=(),
        provider="manual",
    )

    serialized_keys = set(result.model_dump(mode="json"))

    assert "raw_prompt" not in serialized_keys
    assert "provider_payload" not in serialized_keys
    assert "chain_of_thought" not in serialized_keys
    assert result.reference_prices[0].currency == "VND"
