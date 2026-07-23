"""Service shell for reference price research orchestration."""

from __future__ import annotations

from app.price_research.exceptions import (
    PriceResearchDisabledError,
    PriceResearchProviderError,
)
from app.price_research.providers import (
    PriceResearchProvider,
    get_price_research_provider,
)
from app.price_research.schemas import PriceResearchRequest, PriceResearchResult


class PriceResearchService:
    """Coordinate provider-independent reference price research.

    The service has no built-in web provider and performs no external network
    access. It only enforces disabled-by-default settings and delegates to an
    explicitly supplied provider when enabled.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        provider: PriceResearchProvider | None = None,
        provider_name: str = "fake",
        timeout_seconds: int = 30,
        max_sources: int = 5,
    ) -> None:
        self.enabled = enabled
        self.provider = provider
        self.provider_name = provider_name.strip() or "fake"
        self.timeout_seconds = timeout_seconds
        self.max_sources = max_sources

    async def research_price(
        self,
        request: PriceResearchRequest,
    ) -> PriceResearchResult:
        """Return reference price evidence from the configured provider."""
        if not self.enabled:
            raise PriceResearchDisabledError("Price research is disabled")
        provider = self.provider or get_price_research_provider(self.provider_name)

        result = await provider.research_price(request)
        if len(result.sources) > self.max_sources:
            raise PriceResearchProviderError(
                "Price research provider returned too many sources",
            )
        return result
