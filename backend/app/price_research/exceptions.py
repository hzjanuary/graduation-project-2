"""Typed exceptions for reference price research."""


class PriceResearchError(RuntimeError):
    """Base error for safe reference price research failures."""


class PriceResearchDisabledError(PriceResearchError):
    """Raised when price research is requested while disabled by settings."""


class PriceResearchProviderError(PriceResearchError):
    """Raised when a configured price research provider fails safely."""


class PriceResearchValidationError(PriceResearchError):
    """Raised when price research input or output cannot be normalized safely."""
