"""Deterministic fake reference price research provider."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.price_research.schemas import (
    PriceResearchRequest,
    PriceResearchResult,
    PriceResearchSource,
    PriceResearchSourceType,
    ReferencePrice,
)

FAKE_REFERENCE_RETRIEVED_AT = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
FAKE_PROVIDER_WARNING = (
    "Fake provider output is deterministic demo reference evidence, "
    "not a final quote."
)
STANDARD_BUSINESS_LAPTOP = "standard business laptop"


class FakePriceResearchProvider:
    """No-network fake provider for deterministic tests and demos.

    Returned data is explicitly fake reference evidence only. It is not a final
    quote, stock promise, delivery promise, discount approval, or substitute for
    the human approval lifecycle.
    """

    name = "fake"

    async def research_price(
        self,
        request: PriceResearchRequest,
    ) -> PriceResearchResult:
        """Return deterministic fake reference evidence for supported items."""
        if request.normalized_item_name.strip().lower() != STANDARD_BUSINESS_LAPTOP:
            return PriceResearchResult(
                item_name=request.item_name,
                normalized_item_name=request.normalized_item_name,
                quantity=request.quantity,
                region=request.region,
                currency=request.currency,
                reference_prices=(),
                sources=(),
                confidence=0.1,
                retrieved_at=FAKE_REFERENCE_RETRIEVED_AT,
                warnings=(
                    "No fake catalog match for requested item; "
                    "manual research is required.",
                    FAKE_PROVIDER_WARNING,
                ),
                provider=self.name,
            )

        source = PriceResearchSource(
            title="Fake laptop reference fixture",
            url=None,
            snippet=(
                "Deterministic demo fixture for Standard business laptop "
                "reference evidence."
            ),
            observed_price=Decimal("12000000"),
            currency=request.currency,
            retrieved_at=FAKE_REFERENCE_RETRIEVED_AT,
            source_type=PriceResearchSourceType.FAKE,
            confidence=0.85,
        )
        reference_price = ReferencePrice(
            label="Reference unit price",
            amount=Decimal("12000000"),
            currency=request.currency,
            unit="unit",
            quantity_basis=1,
            source_index=0,
            notes="Fake demo reference evidence only; human approval remains required.",
        )
        return PriceResearchResult(
            item_name=request.item_name,
            normalized_item_name=request.normalized_item_name,
            quantity=request.quantity,
            region=request.region,
            currency=request.currency,
            reference_prices=(reference_price,),
            sources=(source,),
            confidence=0.85,
            retrieved_at=FAKE_REFERENCE_RETRIEVED_AT,
            warnings=(FAKE_PROVIDER_WARNING,),
            provider=self.name,
        )
