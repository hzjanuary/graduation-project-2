"""Manual no-network reference price research provider."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from app.price_research.schemas import (
    PriceResearchRequest,
    PriceResearchResult,
    PriceResearchSource,
    PriceResearchSourceType,
    ReferencePrice,
)

MANUAL_RESEARCH_REQUIRED_WARNING = (
    "Manual price research is required; no configured manual reference data "
    "was provided."
)


class ManualPriceResearchProvider:
    """No-network provider backed only by explicit constructor data.

    Manual data is still reference evidence only. It must not be treated as a
    final quotation, stock promise, delivery promise, or approval decision.
    """

    name = "manual"

    def __init__(
        self,
        *,
        sources: Sequence[PriceResearchSource] = (),
        reference_prices: Sequence[ReferencePrice] = (),
        confidence: float = 0.0,
        warnings: Sequence[str] = (),
        retrieved_at: datetime | None = None,
    ) -> None:
        self._sources = tuple(_as_manual_source(source) for source in sources)
        self._reference_prices = tuple(reference_prices)
        self._confidence = confidence
        self._warnings = tuple(warnings)
        self._retrieved_at = retrieved_at

    async def research_price(
        self,
        request: PriceResearchRequest,
    ) -> PriceResearchResult:
        """Return explicitly configured manual reference evidence, if any."""
        if not self._sources and not self._reference_prices:
            return PriceResearchResult(
                item_name=request.item_name,
                normalized_item_name=request.normalized_item_name,
                quantity=request.quantity,
                region=request.region,
                currency=request.currency,
                reference_prices=(),
                sources=(),
                confidence=0.0,
                retrieved_at=self._retrieved_at or datetime.now(UTC),
                warnings=(MANUAL_RESEARCH_REQUIRED_WARNING,),
                provider=self.name,
            )

        return PriceResearchResult(
            item_name=request.item_name,
            normalized_item_name=request.normalized_item_name,
            quantity=request.quantity,
            region=request.region,
            currency=request.currency,
            reference_prices=self._reference_prices,
            sources=self._sources,
            confidence=self._confidence,
            retrieved_at=self._retrieved_at or datetime.now(UTC),
            warnings=self._warnings,
            provider=self.name,
        )


def _as_manual_source(source: PriceResearchSource) -> PriceResearchSource:
    return source.model_copy(update={"source_type": PriceResearchSourceType.MANUAL})
