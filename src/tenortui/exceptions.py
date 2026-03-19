class ProviderError(Exception):
    """Base exception for all provider errors."""


class SymbolNotFoundError(ProviderError):
    """Raised when a ticker symbol is not recognized by the provider."""


class ConfigError(Exception):
    """Raised for config file parsing or validation errors."""
